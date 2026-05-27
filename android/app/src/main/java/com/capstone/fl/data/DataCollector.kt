package com.capstone.fl.data

import android.content.Context
import kotlin.random.Random

/** Background data collector — the "Gboard pattern".
 *
 *  Instead of training on a pre-downloaded dataset, a Collector watches
 *  whatever signal the device naturally produces (keyboard input, sensor
 *  reads, photos, health data, …), self-labels it, persists locally, and
 *  exposes the accumulated buffer when FLWorker fires. The point of this
 *  abstraction is that FLWorker doesn't care which signal — it just asks
 *  "do we have enough to train?" and "give me the next batch".
 *
 *  The concrete implementations (InputMethodService listener, camera
 *  capture, sensor logger, …) are domain-specific and intentionally out of
 *  scope of this capstone. We ship two placeholders so the rest of the
 *  pipeline is exercisable today, and any future collector slots in by
 *  registering itself with [CollectorRegistry]. */
interface DataCollector {
    /** Stable name surfaced in the UI and Settings. */
    val name: String

    /** How many *unused* on-device samples have been collected so far. */
    fun count(ctx: Context): Int

    /** Minimum samples this collector wants before triggering a round.
     *  FLWorker skips training (Result.success) when count < minBatch. */
    val minBatch: Int get() = 32

    /** Take the next chunk of (x, y) and clear it from the buffer. Return
     *  null if there isn't enough yet (collector is silent — no training). */
    fun drain(ctx: Context, batchSize: Int): Iterable<Pair<FloatArray, IntArray>>?

    /** Wipe any persisted state (user opt-out, privacy reset, etc). */
    fun reset(ctx: Context) {}

    /** Optional: an FYI label shown in the participant UI so the user knows
     *  what they're contributing. e.g. "키보드 다음 단어 예측". */
    val description: String get() = name
}


/** Default. Means "no live collection — train on the registered static
 *  DatasetLoader instead (current behaviour)". Keeps existing demos working. */
class NoopCollector : DataCollector {
    override val name = "none"
    override val description = "정적 데이터셋 사용 (수집 안함)"
    override fun count(ctx: Context) = 0
    override fun drain(ctx: Context, batchSize: Int) = null
}


/** Demo collector. Synthesises one mock 28x28 sample every time count() is
 *  read until it hits minBatch, so the rest of the UI ("32 / 32 ready")
 *  animates correctly during a presentation even with no real input source
 *  hooked up. Not a real classifier — pure scaffolding. */
class MockCollector : DataCollector {
    override val name = "mock"
    override val description = "데모용 가짜 수집기 (자동 누적)"
    override val minBatch: Int get() = 32

    private val rng = Random(42)
    @Volatile private var produced = 0
    private val xs = mutableListOf<FloatArray>()
    private val ys = mutableListOf<Int>()

    @Synchronized
    private fun tickProduce() {
        // Drip-feed up to minBatch samples to keep the demo monotonic.
        while (produced < minBatch) {
            xs += FloatArray(28 * 28) { rng.nextFloat() }
            ys += rng.nextInt(10)
            produced += 1
        }
    }

    @Synchronized
    override fun count(ctx: Context): Int {
        tickProduce()
        return xs.size
    }

    @Synchronized
    override fun drain(ctx: Context, batchSize: Int): Iterable<Pair<FloatArray, IntArray>>? {
        tickProduce()
        if (xs.size < minBatch) return null
        val out = ArrayList<Pair<FloatArray, IntArray>>()
        var i = 0
        while (i < xs.size) {
            val end = minOf(i + batchSize, xs.size)
            val bx = FloatArray((end - i) * 28 * 28)
            val by = IntArray(end - i)
            for (j in i until end) {
                System.arraycopy(xs[j], 0, bx, (j - i) * 28 * 28, 28 * 28)
                by[j - i] = ys[j]
            }
            out += bx to by
            i = end
        }
        xs.clear(); ys.clear(); produced = 0
        return out
    }

    @Synchronized
    override fun reset(ctx: Context) { xs.clear(); ys.clear(); produced = 0 }
}


object CollectorRegistry {
    private val items = mutableMapOf<String, () -> DataCollector>()
    fun register(name: String, factory: () -> DataCollector) { items[name] = factory }
    fun get(name: String): DataCollector = (items[name] ?: items["none"]!!).invoke()
    fun available(): List<String> = items.keys.sorted()

    init {
        register("none") { NoopCollector() }
        register("mock") { MockCollector() }
        // Future: register("keyboard") { KeyboardInputCollector() }
        // Future: register("camera")   { CameraCaptureCollector() }
        // Future: register("sensor")   { SensorLogCollector() }
    }
}
