package com.capstone.fl.data

import kotlin.random.Random

/** Stub MNIST data — replace with real on-device tensors / bundled files. */
class MnistLoader : DatasetLoader {
    override val name = "mnist"
    private val n = 1000
    private val rng = Random(0)
    private val xs = Array(n) { FloatArray(28 * 28) { rng.nextFloat() } }
    private val ys = IntArray(n) { rng.nextInt(10) }

    override fun size() = n
    override fun load(indices: IntArray?, batchSize: Int): Iterable<Pair<FloatArray, IntArray>> {
        val idx = indices ?: IntArray(n) { it }
        return sequence {
            var i = 0
            while (i < idx.size) {
                val end = minOf(i + batchSize, idx.size)
                val bx = FloatArray((end - i) * 28 * 28)
                val by = IntArray(end - i)
                for (j in i until end) {
                    System.arraycopy(xs[idx[j]], 0, bx, (j - i) * 28 * 28, 28 * 28)
                    by[j - i] = ys[idx[j]]
                }
                yield(bx to by)
                i = end
            }
        }.asIterable()
    }
}
