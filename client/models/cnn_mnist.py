import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .base import ModelRunner
from .registry import register


class CnnMnistModule(nn.Module):
    """Must mirror backend/server/models/cnn_mnist.py exactly so state_dicts swap."""

    def __init__(self) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, 3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc = nn.Linear(32 * 7 * 7, 10)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        return self.fc(x.flatten(1))


@register
class CnnMnistRunner(ModelRunner):
    """Real PyTorch trainer. Weights are exchanged with the server as plain
    {layer_name: nested-list} dicts so the on-the-wire format stays framework-
    agnostic — only this file knows about torch."""

    name = "cnn_mnist"

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CnnMnistModule().to(self.device)
        self.criterion = nn.CrossEntropyLoss()

    def get_weights(self):
        return {k: v.detach().cpu().numpy().tolist() for k, v in self.model.state_dict().items()}

    def set_weights(self, weights):
        sd = {k: torch.tensor(np.asarray(v), dtype=torch.float32) for k, v in weights.items()}
        self.model.load_state_dict(sd, strict=False)

    def train(self, data, epochs=1):
        opt = torch.optim.SGD(self.model.parameters(), lr=0.01, momentum=0.9)
        self.model.train()
        total_loss = 0.0
        total_n = 0
        correct = 0
        for _ in range(epochs):
            for x, y in data:
                x = torch.as_tensor(x, dtype=torch.float32, device=self.device)
                y = torch.as_tensor(y, dtype=torch.long, device=self.device)
                if x.dim() == 3:  # (B, 28, 28) → (B, 1, 28, 28)
                    x = x.unsqueeze(1)
                opt.zero_grad()
                out = self.model(x)
                loss = self.criterion(out, y)
                loss.backward()
                opt.step()
                bs = y.size(0)
                total_loss += loss.item() * bs
                total_n += bs
                correct += (out.argmax(1) == y).sum().item()
        return {
            "loss": float(total_loss / max(total_n, 1)),
            "accuracy": float(correct / max(total_n, 1)),
            "epochs": epochs,
        }

    def evaluate(self, data):
        self.model.eval()
        correct = 0; n = 0; loss_sum = 0.0
        with torch.no_grad():
            for x, y in data:
                x = torch.as_tensor(x, dtype=torch.float32, device=self.device)
                y = torch.as_tensor(y, dtype=torch.long, device=self.device)
                if x.dim() == 3: x = x.unsqueeze(1)
                out = self.model(x)
                loss_sum += self.criterion(out, y).item() * y.size(0)
                correct += (out.argmax(1) == y).sum().item()
                n += y.size(0)
        return {"loss": float(loss_sum / max(n, 1)),
                "accuracy": float(correct / max(n, 1))}
