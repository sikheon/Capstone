package com.capstone.fl.data

/** Owns the actual on-device data. Swap implementations to plug in MNIST,
 * CIFAR-10, sensor logs, photos, etc. without touching the rest of the app. */
interface DatasetLoader {
    val name: String
    fun size(): Int
    fun load(indices: IntArray? = null, batchSize: Int = 32): Iterable<Pair<FloatArray, IntArray>>
}

object DatasetRegistry {
    private val items = mutableMapOf<String, () -> DatasetLoader>()
    fun register(name: String, factory: () -> DatasetLoader) { items[name] = factory }
    fun get(name: String): DatasetLoader = (items[name]
        ?: error("dataset '$name' not registered. available=${items.keys}")).invoke()
    fun available(): List<String> = items.keys.sorted()

    init {
        register("mnist")         { MnistLoader() }
        register("fashion_mnist") { FashionMnistLoader() }
    }
}
