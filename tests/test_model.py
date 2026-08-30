import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from model import get_model


def test_resnet18_output_shape():
    model = get_model(architecture="resnet18", num_classes=10)
    x = torch.randn(2, 3, 32, 32)
    output = model(x)
    assert output.shape == (2, 10)


def test_cnn_output_shape():
    model = get_model(architecture="cnn", num_classes=10)
    x = torch.randn(2, 3, 32, 32)
    output = model(x)
    assert output.shape == (2, 10)


def test_unknown_architecture_raises():
    try:
        get_model(architecture="does-not-exist", num_classes=10)
        assert False, "expected ValueError"
    except ValueError:
        pass
