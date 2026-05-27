package com.capstone.fl.fl

import com.capstone.fl.model.ModelRunner

/** Client-side FL algorithm. Swap to change how the device transforms global
 * weights → local update. Server-side aggregation lives in the Python coordinator. */
interface FLAlgorithm {
    val name: String

    /** @return (newWeights, metrics) */
    fun localTrain(
        runner: ModelRunner,
        globalWeights: Map<String, FloatArray>,
        data: Iterable<Pair<FloatArray, IntArray>>,
        epochs: Int,
    ): Pair<Map<String, FloatArray>, Map<String, Float>>
}

object AlgorithmRegistry {
    private val items = mutableMapOf<String, FLAlgorithm>()
    fun register(a: FLAlgorithm) { items[a.name] = a }
    fun get(name: String): FLAlgorithm = items[name]
        ?: error("algorithm '$name' not registered. available=${items.keys}")
    fun available(): List<String> = items.keys.sorted()

    init { register(FedAvgClient()) }
}

class FedAvgClient : FLAlgorithm {
    override val name = "fedavg"
    override fun localTrain(
        runner: ModelRunner,
        globalWeights: Map<String, FloatArray>,
        data: Iterable<Pair<FloatArray, IntArray>>,
        epochs: Int,
    ): Pair<Map<String, FloatArray>, Map<String, Float>> {
        runner.setWeights(globalWeights)
        val metrics = runner.train(data, epochs)
        return runner.getWeights() to metrics
    }
}
