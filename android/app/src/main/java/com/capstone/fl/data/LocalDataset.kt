package com.capstone.fl.data

import android.content.Context
import org.json.JSONObject
import java.io.File

/** On-device cache of a server-pushed sample dataset.
 *
 * The server sends:
 *   { "name": "mnist", "n": 200, "h": 28, "w": 28, "num_classes": 10,
 *     "x": [[float * h*w], ...], "y": [int, ...] }
 *
 * We persist that JSON under filesDir/datasets/<name>.json and parse it back
 * into FloatArray/IntArray on load. Small (~2-3 MB for 200 samples) so JSON
 * is fine; for larger bundles swap in a binary format. */
class LocalDataset(private val ctx: Context) {

    private val dir = File(ctx.filesDir, "datasets").apply { mkdirs() }

    fun save(name: String, payload: JSONObject) {
        File(dir, "$name.json").writeText(payload.toString())
    }

    fun isInstalled(name: String) = File(dir, "$name.json").exists()

    fun load(name: String): Bundle? {
        val f = File(dir, "$name.json")
        if (!f.exists()) return null
        val obj = JSONObject(f.readText())
        val n = obj.getInt("n")
        val h = obj.optInt("h", 28)
        val w = obj.optInt("w", 28)
        val xs = obj.getJSONArray("x")
        val ys = obj.getJSONArray("y")
        val x = Array(n) { FloatArray(h * w) }
        val y = IntArray(n)
        for (i in 0 until n) {
            val row = xs.getJSONArray(i)
            val xi = x[i]
            for (j in 0 until row.length()) xi[j] = row.getDouble(j).toFloat()
            y[i] = ys.getInt(i)
        }
        return Bundle(name, h, w, x, y)
    }

    fun delete(name: String): Boolean = File(dir, "$name.json").delete()

    data class Bundle(val name: String, val h: Int, val w: Int,
                      val x: Array<FloatArray>, val y: IntArray) {
        fun size() = x.size
        fun batches(batchSize: Int): Iterable<Pair<FloatArray, IntArray>> = sequence {
            var i = 0
            while (i < size()) {
                val end = minOf(i + batchSize, size())
                val bx = FloatArray((end - i) * h * w)
                val by = IntArray(end - i)
                for (j in i until end) {
                    System.arraycopy(x[j], 0, bx, (j - i) * h * w, h * w)
                    by[j - i] = y[j]
                }
                yield(bx to by)
                i = end
            }
        }.asIterable()
    }
}
