"""All swappable categories should expose their default implementations."""

from server import algorithms, models, datasets, selection, dropout, transport


def test_default_registries_populated():
    assert "fedavg" in algorithms.available()
    assert "cnn_mnist" in models.available()
    assert "mnist" in datasets.available()
    assert "all" in selection.available()
    assert "random" in selection.available()
    assert "dropout_aware" in selection.available()
    assert "rule_based" in dropout.available()
    assert "http" in transport.available()


def test_unknown_lookup_errors():
    import pytest
    with pytest.raises(KeyError):
        algorithms.get("nope")
    with pytest.raises(KeyError):
        models.get("nope")
