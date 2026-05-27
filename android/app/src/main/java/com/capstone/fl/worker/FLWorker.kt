package com.capstone.fl.worker

import android.content.Context
import android.os.BatteryManager
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.capstone.fl.Settings
import com.capstone.fl.data.CollectorRegistry
import com.capstone.fl.data.DatasetRegistry
import com.capstone.fl.fl.AlgorithmRegistry
import com.capstone.fl.model.ModelRegistry
import com.capstone.fl.network.FLApi
import com.capstone.fl.reporter.LocalReporter
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.max
import kotlin.math.min

/** Gboard-style FL participant. Wakes up under WorkManager's Constraints
 * (charging + unmetered + idle + battery-not-low) and runs ONE full FL cycle:
 *
 *   1. heartbeat → if server says "selected_for_round" or async mode → continue
 *   2. extra eligibility check (battery ≥ 50% as a belt-and-braces guard)
 *   3. fetch global weights via GET /api/round/current
 *   4. load global weights into the local ModelRunner
 *   5. run one local SGD-ish step against the on-device dataset
 *   6. POST /api/update with the new weights + metrics
 *
 * The worker is short-lived — WorkManager re-runs it on its own schedule. */
class FLWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result {
        val ctx = applicationContext
        val settings = Settings(ctx)

        // ----- belt-and-braces battery check (Constraints already enforce most of this) -----
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager?
        val pct = bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: 100
        if (pct < 50) return Result.retry()

        // ----- credentials -----
        settings.updateStage("연결 중")
        val api = FLApi(settings.serverUrl, settings.clientId, settings.clientSecret)
        if (api.clientId == null || api.clientSecret == null) {
            try {
                val (id, sec) = api.provision()
                settings.clientId = id; settings.clientSecret = sec
            } catch (e: Exception) { settings.updateStage(""); return Result.retry() }
        }

        // ----- heartbeat -----
        val reporter = LocalReporter(ctx)
        val resp = try {
            api.heartbeat(reporter.snapshot(api.clientId ?: "android"))
        } catch (e: Exception) { settings.updateStage(""); return Result.retry() }

        val state = resp.optString("orchestrator_state")
        val mode = resp.optString("mode")
        val selected = resp.optBoolean("selected_for_round", false)
        val epochs = resp.optInt("local_epochs", 1)

        // Follow server-driven swaps. The dashboard's "swap dataset to fashion_mnist"
        // is meaningless if the phone keeps grinding on MNIST — so we mirror what
        // the coordinator says it's running.
        resp.optString("algorithm").takeIf { it.isNotBlank() && it != settings.algorithm }
            ?.let { settings.algorithm = it }
        resp.optString("model").takeIf { it.isNotBlank() && it != settings.model }
            ?.let { settings.model = it }
        resp.optString("dataset").takeIf { it.isNotBlank() && it != settings.dataset }
            ?.let { settings.dataset = it }

        if (state != "running") { settings.updateStage(""); return Result.success() }
        if (mode == "sync" && !selected) { settings.updateStage(""); return Result.success() }

        // ----- fetch global weights -----
        settings.updateStage("가중치 다운로드")
        val current = try { api.currentRound() } catch (_: Exception) { settings.updateStage(""); return Result.retry() }
        val weights = current.optJSONObject("weights") ?: run { settings.updateStage(""); return Result.success() }

        // ----- pluggable algorithm / model / data source -----
        val algo = AlgorithmRegistry.get(settings.algorithm)
        val runner = ModelRegistry.get(settings.model)

        // If a background collector is wired (Gboard-pattern), train on what
        // it has buffered; otherwise use the static DatasetLoader.
        val collector = CollectorRegistry.get(settings.collector)
        val collected = collector.drain(ctx, batchSize = 32)
        val batches: Iterable<Pair<FloatArray, IntArray>>
        val numSamples: Int
        if (collected != null) {
            settings.updateStage("수집 데이터로 학습 중")
            val materialised = collected.toList()
            batches = materialised
            numSamples = materialised.sumOf { it.second.size }
        } else if (collector.name != "none") {
            // Collector exists but doesn't have enough yet — defer training,
            // come back when WorkManager fires next.
            settings.updateStage("")
            return Result.success()
        } else {
            settings.updateStage("로컬 학습 중")
            val ds = DatasetRegistry.get(settings.dataset)
            batches = ds.load(batchSize = 32)
            numSamples = ds.size()
        }

        val wMap = jsonToWeights(weights)
        val (newW, metrics) = algo.localTrain(runner, wMap, batches, epochs)

        // ----- submit update -----
        settings.updateStage("결과 업로드")
        try {
            api.submitUpdate(
                JSONObject()
                    .put("client_id", api.clientId)
                    .put("weights", weightsToJson(newW))
                    .put("num_samples", numSamples)
                    .put("metrics", JSONObject().apply {
                        for ((k, v) in metrics) put(k, v.toDouble())
                    })
            )
        } catch (_: Exception) { settings.updateStage(""); return Result.retry() }

        // ----- local ledger for UI -----
        settings.bumpContribution(
            acc = metrics["accuracy"]?.toFloat() ?: -1f,
            loss = metrics["loss"]?.toFloat() ?: -1f,
        )
        settings.updateStage("")
        return Result.success()
    }

    private fun jsonToWeights(obj: JSONObject): Map<String, FloatArray> {
        // The server ships weights as nested float lists keyed by layer name.
        // We flatten to FloatArray; shape recovery happens server-side via reshape().
        val out = HashMap<String, FloatArray>(obj.length())
        val keys = obj.keys()
        while (keys.hasNext()) {
            val k = keys.next()
            val flat = ArrayList<Float>(1024)
            flattenInto(obj.get(k), flat)
            val arr = FloatArray(flat.size)
            for (i in arr.indices) arr[i] = flat[i]
            out[k] = arr
        }
        return out
    }

    private fun flattenInto(v: Any?, sink: ArrayList<Float>) {
        when (v) {
            is JSONArray -> for (i in 0 until v.length()) flattenInto(v.get(i), sink)
            is Number -> sink.add(v.toFloat())
            else -> {}
        }
    }

    private fun weightsToJson(weights: Map<String, FloatArray>): JSONObject {
        val obj = JSONObject()
        for ((k, arr) in weights) {
            val ja = JSONArray()
            for (x in arr) ja.put(x.toDouble())
            obj.put(k, ja)
        }
        return obj
    }
}
