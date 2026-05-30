from .base import ClientAlgorithm
from .registry import register


@register
class FedAvgClient(ClientAlgorithm):
    """Vanilla local SGD; server averages the results."""

    name = "fedavg"

    def local_train(self, model_runner, global_weights, data, epochs):
        model_runner.set_weights(global_weights)
        metrics = model_runner.train(data, epochs=epochs)
        return model_runner.get_weights(), metrics
