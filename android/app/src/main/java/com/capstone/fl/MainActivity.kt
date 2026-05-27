package com.capstone.fl

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Bundle
import android.os.PowerManager
import android.view.LayoutInflater
import android.view.View
import android.widget.EditText
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import android.widget.ArrayAdapter
import android.widget.Spinner
import com.capstone.fl.data.CollectorRegistry
import com.capstone.fl.databinding.ActivityMainBinding
import com.capstone.fl.network.FLApi
import com.capstone.fl.worker.FLScheduler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Single-screen participant UI. */
class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding
    private lateinit var settings: Settings
    private var pollJob: Job? = null
    private val ui = CoroutineScope(Dispatchers.Main)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)
        settings = Settings(this)

        b.joinSwitch.isChecked = FLScheduler.isPeriodicEnabled(this)
        b.joinSwitch.setOnCheckedChangeListener { _, on ->
            if (on) FLScheduler.enablePeriodic(this) else FLScheduler.disablePeriodic(this)
            paintState()
        }
        b.runOnceBtn.setOnClickListener { FLScheduler.runOnce(this) }
        b.settingsBtn.setOnClickListener { showSettingsDialog() }

        // KPI / cond labels
        b.kpiContributed.kpiLabel.text = getString(R.string.kpi_contributed)
        b.kpiMyAcc.kpiLabel.text       = getString(R.string.kpi_my_acc)
        b.kpiGlobalAcc.kpiLabel.text   = getString(R.string.kpi_global_acc)
        b.condCharging.condLabel.text  = getString(R.string.cond_charging)
        b.condWifi.condLabel.text      = getString(R.string.cond_wifi)
        b.condBattery.condLabel.text   = getString(R.string.cond_battery)
        b.condIdle.condLabel.text      = getString(R.string.cond_idle)

        // fleet chips
        b.fleetAndroid.chipIcon.text = "📱"; b.fleetAndroid.chipLabel.text = getString(R.string.fleet_android)
        b.fleetEdge.chipIcon.text    = "🖥"; b.fleetEdge.chipLabel.text    = getString(R.string.fleet_edge)
        b.fleetCli.chipIcon.text     = "⌨"; b.fleetCli.chipLabel.text     = getString(R.string.fleet_cli)

        paintState(); paintConditions(); paintLedger(); paintSparkline(); paintCollector()
    }

    override fun onResume() {
        super.onResume()
        pollJob = ui.launch {
            while (isActive) {
                paintState()
                paintConditions()
                paintLedger()
                paintSparkline()
                paintCollector()
                refreshGlobalAcc()
                refreshFleet()
                delay(2_500)
            }
        }
    }

    override fun onPause() {
        super.onPause(); pollJob?.cancel(); pollJob = null
    }
    override fun onDestroy() {
        super.onDestroy(); ui.cancel()
    }

    // ───── state painters ───────────────────────────────────────────────────

    private fun paintState() {
        val joined = b.joinSwitch.isChecked
        val stage  = settings.stage
        val live   = stage.isNotBlank() &&
                     System.currentTimeMillis() - settings.stageAt < 5 * 60 * 1000

        if (live) {
            b.stateLabel.text = getString(R.string.state_training)
            b.stateHint.text  = stage
            b.statusDot.setBackgroundResource(R.drawable.dot_training)
            b.progressBar.visibility = View.VISIBLE
        } else {
            b.stateLabel.text = getString(if (joined) R.string.state_joined else R.string.state_idle)
            b.stateHint.text  = getString(if (joined) R.string.hint_joined  else R.string.hint_idle)
            b.statusDot.setBackgroundResource(if (joined) R.drawable.dot_joined else R.drawable.dot_idle)
            b.progressBar.visibility = View.GONE
        }

        val id = settings.clientId
        b.clientIdLabel.text = if (id != null)
            "${getString(R.string.footer_client_id)}: $id"
        else
            "${getString(R.string.footer_client_id)}: ${getString(R.string.footer_not_provisioned)}"
    }

    private fun paintConditions() {
        setCond(b.condCharging.condIcon, isCharging())
        setCond(b.condWifi.condIcon, isUnmeteredWifi())
        setCond(b.condBattery.condIcon, batteryPct() >= 50)
        setCond(b.condIdle.condIcon, isDeviceIdle())
    }
    private fun setCond(view: android.widget.TextView, ok: Boolean) {
        view.text = if (ok) "✓" else "·"
        view.setTextColor(getColor(if (ok) R.color.ok else R.color.ink_muted))
    }

    private fun paintLedger() {
        b.kpiContributed.kpiValue.text = settings.contributedRounds.toString()
        b.kpiContributed.kpiHint.text  = if (settings.lastContributedAt > 0)
            humanAgo(settings.lastContributedAt) else "아직 없음"

        val acc = settings.lastTrainAcc
        b.kpiMyAcc.kpiValue.text = if (acc >= 0) "${"%.2f".format(acc * 100)}%" else "—"
        b.kpiMyAcc.kpiHint.text  = if (settings.lastTrainLoss >= 0)
            "loss ${"%.3f".format(settings.lastTrainLoss)}" else ""
    }

    private fun paintCollector() {
        val collector = CollectorRegistry.get(settings.collector)
        val count = collector.count(this)
        val target = collector.minBatch
        b.collectorName.text = collector.name
        b.collectorCount.text = "$count / $target"
        b.collectorBar.progress = if (target == 0) 0 else
            (count.coerceAtMost(target) * 100 / target)
        b.collectorHint.text = when {
            collector.name == "none" -> getString(R.string.collector_none_hint)
            count >= target          -> "${collector.description} · ${getString(R.string.collector_ready)}"
            else                     -> "${collector.description} · ${getString(R.string.collector_buffering)}"
        }
    }

    private fun paintSparkline() {
        val hist = settings.accHistory
        b.sparkline.setData(hist.toFloatArray())
        b.sparkRange.text = if (hist.isEmpty()) "" else {
            val mn = hist.min(); val mx = hist.max()
            "${"%.1f".format(mn * 100)}–${"%.1f".format(mx * 100)}%"
        }
    }

    private fun refreshGlobalAcc() {
        ui.launch {
            val result = withContext(Dispatchers.IO) {
                try {
                    val api = FLApi(settings.serverUrl)
                    val ge = api.globalEval()?.optJSONObject("current")
                    if (ge != null) {
                        val a = ge.optDouble("test_accuracy", Double.NaN)
                        val r = ge.optInt("round", -1)
                        if (!a.isNaN()) return@withContext Triple(a, r, "test")
                    }
                    val lm = api.latestMetric() ?: return@withContext null
                    val a = lm.optDouble("accuracy", Double.NaN)
                    val r = lm.optInt("round", -1)
                    if (a.isNaN()) null else Triple(a, r, "train")
                } catch (_: Exception) { null }
            }
            if (result == null) {
                b.kpiGlobalAcc.kpiValue.text = "—"
                b.kpiGlobalAcc.kpiHint.text  = "평가 대기"
            } else {
                val (acc, round, kind) = result
                b.kpiGlobalAcc.kpiValue.text = "${"%.2f".format(acc * 100)}%"
                b.kpiGlobalAcc.kpiHint.text  = "round $round · $kind"
            }
        }
    }

    private fun refreshFleet() {
        ui.launch {
            val counts = withContext(Dispatchers.IO) {
                try {
                    val api = FLApi(settings.serverUrl)
                    val list = api.clients().filter { it.optBoolean("active", false) }
                    val grouped = HashMap<String, Int>()
                    for (c in list) {
                        val k = c.optString("kind", "edge").lowercase()
                        grouped[k] = (grouped[k] ?: 0) + 1
                    }
                    grouped
                } catch (_: Exception) { null }
            }
            if (counts == null) {
                b.fleetOffline.visibility = View.VISIBLE
                b.fleetAndroid.chipCount.text = "0"
                b.fleetEdge.chipCount.text = "0"
                b.fleetCli.chipCount.text = "0"
            } else {
                b.fleetOffline.visibility = View.GONE
                b.fleetAndroid.chipCount.text = (counts["android"] ?: 0).toString()
                b.fleetEdge.chipCount.text    = (counts["edge"] ?: 0).toString()
                // CLI kind in this project is logged as kind="cli"; sim counts here too
                // so the user just sees "everyone else who isn't android or edge".
                val other = (counts["cli"] ?: 0) + (counts["sim"] ?: 0)
                b.fleetCli.chipCount.text     = other.toString()
            }
        }
    }

    // ───── system probes ────────────────────────────────────────────────────

    private fun isCharging(): Boolean {
        val i: Intent? = registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val st = i?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        return st == BatteryManager.BATTERY_STATUS_CHARGING || st == BatteryManager.BATTERY_STATUS_FULL
    }
    private fun batteryPct(): Int {
        val bm = getSystemService(Context.BATTERY_SERVICE) as BatteryManager?
        return bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: 0
    }
    private fun isUnmeteredWifi(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val n = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(n) ?: return false
        return caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) &&
               caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
    }
    private fun isDeviceIdle(): Boolean {
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        return !pm.isInteractive
    }

    // ───── settings ─────────────────────────────────────────────────────────

    private fun showSettingsDialog() {
        val view = LayoutInflater.from(this).inflate(R.layout.dialog_settings, null, false)
        val urlEdit = view.findViewById<EditText>(R.id.dialogServerUrl)
        urlEdit.setText(settings.serverUrl)

        val collectorSpinner = view.findViewById<Spinner>(R.id.dialogCollector)
        val options = CollectorRegistry.available()
        collectorSpinner.adapter = ArrayAdapter(this,
            android.R.layout.simple_spinner_dropdown_item, options)
        collectorSpinner.setSelection(options.indexOf(settings.collector).coerceAtLeast(0))

        AlertDialog.Builder(this)
            .setTitle(R.string.settings_title)
            .setView(view)
            .setPositiveButton(R.string.settings_save) { _, _ ->
                settings.serverUrl = urlEdit.text.toString().trim()
                settings.collector = options[collectorSpinner.selectedItemPosition]
                paintCollector()
            }
            .setNeutralButton(R.string.settings_reprovision) { _, _ ->
                settings.clearCredentials(); paintState()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun humanAgo(ts: Long): String {
        val sec = (System.currentTimeMillis() - ts) / 1000
        return when {
            sec < 60 -> "${sec}초 전"
            sec < 3600 -> "${sec / 60}분 전"
            sec < 86400 -> "${sec / 3600}시간 전"
            else -> "${sec / 86400}일 전"
        }
    }
}
