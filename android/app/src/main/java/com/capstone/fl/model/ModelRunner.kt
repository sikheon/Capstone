package com.capstone.fl.model

/** Trainable model on the device. Swap implementations (TFLite, ONNX, NCNN, …)
 * without touching the FL algorithm or networking layers. */
interface ModelRunner {
    val name: String
    fun getWeights(): Map<String, FloatArray>
    fun setWeights(weights: Map<String, FloatArray>)
    fun train(data: Iterable<Pair<FloatArray, IntArray>>, epochs: Int): Map<String, Float>
    fun evaluate(data: Iterable<Pair<FloatArray, IntArray>>): Map<String, Float>
}

object ModelRegistry {
    private val items = mutableMapOf<String, () -> ModelRunner>()
    fun register(name: String, factory: () -> ModelRunner) { items[name] = factory }
    fun get(name: String): ModelRunner = (items[name]
        ?: error("model '$name' not registered. available=${items.keys}")).invoke()
    fun available(): List<String> = items.keys.sorted()

    init { register("cnn_mnist") { CnnMnistRunner() } }
}
