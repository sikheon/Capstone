package com.capstone.fl.model

import kotlin.random.Random

/** Placeholder NumPy-style runner. Replace with a TFLite/ONNX-backed model —
 * only the four overrides below need to stay matching the [ModelRunner] contract. */
class CnnMnistRunner : ModelRunner {
    override val name = "cnn_mnist"
    private val weights = mutableMapOf<String, FloatArray>()

    override fun getWeights(): Map<String, FloatArray> = weights.toMap()
    override fun setWeights(w: Map<String, FloatArray>) {
        weights.clear(); weights.putAll(w.mapValues { it.value.copyOf() })
    }

    override fun train(data: Iterable<Pair<FloatArray, IntArray>>, epochs: Int): Map<String, Float> {
        val rng = Random.Default
        for ((k, v) in weights) {
            for (i in v.indices) v[i] += rng.nextFloat() * 1e-3f - 5e-4f
        }
        return mapOf("loss" to (0.1f + rng.nextFloat() * 0.4f), "epochs" to epochs.toFloat())
    }

    override fun evaluate(data: Iterable<Pair<FloatArray, IntArray>>): Map<String, Float> =
        mapOf("accuracy" to 0f)
}
