import numpy as np
import torch
import torch.nn as nn

from .base import ModelSpec
from .registry import register


class CnnMnistModule(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, 3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc = nn.Linear(32 * 7 * 7, 10)

    def forward(self, x):
        import torch.nn.functional as F
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        return self.fc(x.flatten(1))


@register
class CnnMnist(ModelSpec):
    """Real CNN for MNIST. Initial weights come from PyTorch's default init
    so clients can immediately fine-tune."""

    name = "cnn_mnist"
    input_shape = (1, 28, 28)
    num_classes = 10

    def initial_weights(self):
        torch.manual_seed(0)
        m = CnnMnistModule()
        return {k: v.detach().cpu().numpy() for k, v in m.state_dict().items()}
