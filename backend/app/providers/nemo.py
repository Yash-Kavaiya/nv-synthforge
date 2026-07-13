from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from app.domain.invoice import Invoice

NVIDIA_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
MODEL_ALIAS = "nemotron-invoice"


class NemoConfigurationError(RuntimeError):
    """Raised when NeMo Data Designer cannot be configured safely."""


class NemoInvoiceProvider:
    """NVIDIA NeMo Data Designer 0.7 adapter for structured invoices."""

    def build_config(self, seed: int):
        try:
            from data_designer.config import (
                ChatCompletionInferenceParams,
                DataDesignerConfigBuilder,
                LLMStructuredColumnConfig,
                ModelConfig,
            )
        except ImportError as exc:
            raise NemoConfigurationError(
                "NeMo provider requires the 'nemo' extra: uv sync --extra nemo"
            ) from exc

        model = ModelConfig(
            alias=MODEL_ALIAS,
            model=NVIDIA_MODEL,
            provider="nvidia",
            inference_parameters=ChatCompletionInferenceParams(
                temperature=0.2,
                extra_body={"seed": seed},
            ),
        )
        column = LLMStructuredColumnConfig(
            name="invoice",
            model_alias=MODEL_ALIAS,
            output_format=Invoice,
            prompt=(
                "Create one realistic Indian GST invoice. All GSTIN prefixes must match "
                f"their address state codes. Generation seed: {seed}."
            ),
        )
        return DataDesignerConfigBuilder(model_configs=[model]).add_column(column)

    def generate(self, count: int, seed: int) -> list[Invoice]:
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise NemoConfigurationError(
                "NVIDIA_API_KEY is required for provider='nemo'; no network request was made"
            )
        if not 1 <= count <= 10_000:
            raise ValueError("count must be between 1 and 10000")

        try:
            from data_designer.interface import DataDesigner
        except ImportError as exc:
            raise NemoConfigurationError(
                "NeMo provider requires the 'nemo' extra: uv sync --extra nemo"
            ) from exc

        results = DataDesigner().create(
            self.build_config(seed),
            num_records=count,
            dataset_name=f"nv-synthforge-invoices-{seed}",
        )
        records = self._extract_records(results)
        return [Invoice.model_validate(record.get("invoice", record)) for record in records]

    @staticmethod
    def _extract_records(results: Any) -> Iterable[dict[str, Any]]:
        if hasattr(results, "to_pandas"):
            return results.to_pandas().to_dict(orient="records")
        if hasattr(results, "dataset"):
            dataset = results.dataset
            if hasattr(dataset, "to_pylist"):
                return dataset.to_pylist()
            return list(dataset)
        if isinstance(results, Iterable) and not isinstance(results, (str, bytes, dict)):
            return list(results)
        raise RuntimeError("NeMo Data Designer returned an unsupported result object")
