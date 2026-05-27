package com.capstone.fl.data

import kotlin.random.Random

/** Stub Fashion-MNIST. Same 28x28 grayscale 10-class shape as MNIST so the
 *  existing CnnMnistRunner accepts it unchanged. Real on-device tensors
 *  come via the server's /api/dataset/fashion_mnist/sample endpoint when the
 *  participant first opts in to this dataset; until then we generate noise
 *  so the worker still has a valid batch shape to exercise. */
class FashionMnistLoader : DatasetLoader {
    override val name = "fashion_mnist"
    private val n = 1000
    private val rng = Random(1)   // seed differs from MNIST so the demo can tell
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
