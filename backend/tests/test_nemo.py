import pytest

from app.providers.nemo import NemoConfigurationError, NemoInvoiceProvider


def test_nemo_provider_fails_clearly_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(NemoConfigurationError, match="NVIDIA_API_KEY"):
        NemoInvoiceProvider().generate(count=1, seed=1)


def test_nemo_builds_data_designer_070_config(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("data_designer")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only-not-used")
    provider = NemoInvoiceProvider()
    builder = provider.build_config(seed=9)
    config = builder.build()
    assert config.model_configs[0].provider == "nvidia"
    assert config.model_configs[0].model == "nvidia/nemotron-3-nano-30b-a3b"
    assert any(column.name == "invoice" and column.column_type == "llm-structured" for column in config.columns)
