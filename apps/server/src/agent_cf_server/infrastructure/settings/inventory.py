"""Runtime and model inventory discovery (SET-001).

Preserves observed model labels without guessing unknown runtime IDs.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiscoveredModel:
    display_name: str
    runtime_model_id: str | None
    access_status: str
    ui_status: str | None = None
    hidden: bool = False


@dataclass(frozen=True)
class RuntimeAdapterInfo:
    adapter_id: str
    observed_cli_version: str | None
    discovery_method: str | None
    models: list[DiscoveredModel]


@dataclass(frozen=True)
class RuntimeInventory:
    schema_version: int
    observed_on: str
    purpose: str
    runtimes: dict[str, RuntimeAdapterInfo]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observed_on": self.observed_on,
            "purpose": self.purpose,
            "runtimes": {
                name: {
                    "adapter_id": adapter.adapter_id,
                    "observed_cli_version": adapter.observed_cli_version,
                    "discovery_method": adapter.discovery_method,
                    "models": [
                        {
                            "display_name": m.display_name,
                            "runtime_model_id": m.runtime_model_id,
                            "access_status": m.access_status,
                            "ui_status": m.ui_status,
                            "hidden": m.hidden,
                        }
                        for m in adapter.models
                    ],
                }
                for name, adapter in self.runtimes.items()
            },
        }


def load_runtime_inventory(reference_path: Path | None = None) -> RuntimeInventory:
    """Load the machine runtime and model inventory from the reference inventory file."""
    if reference_path is None:
        # Default reference path in docs/reports/local-runtime-models.json
        candidate = Path(__file__).resolve().parents[5] / "docs" / "reports" / "local-runtime-models.json"
        if not candidate.exists():
            candidate = Path("docs/reports/local-runtime-models.json").resolve()
        reference_path = candidate

    if not reference_path.exists():
        raise FileNotFoundError(f"Runtime model inventory not found at {reference_path}")

    data = json.loads(reference_path.read_text(encoding="utf-8"))
    runtimes: dict[str, RuntimeAdapterInfo] = {}

    for key, val in data.items():
        if key in ("schema_version", "observed_on", "purpose") or not isinstance(val, dict):
            continue
        models = [
            DiscoveredModel(
                display_name=item["display_name"],
                runtime_model_id=item.get("runtime_model_id"),
                access_status=item.get("access", "unknown"),
                ui_status=item.get("ui_status"),
                hidden=item.get("hidden", False),
            )
            for item in val.get("models", [])
        ]
        runtimes[key] = RuntimeAdapterInfo(
            adapter_id=key,
            observed_cli_version=val.get("observed_cli_version"),
            discovery_method=val.get("discovery") or val.get("source"),
            models=models,
        )

    return RuntimeInventory(
        schema_version=data.get("schema_version", 1),
        observed_on=data.get("observed_on", "unknown"),
        purpose=data.get("purpose", ""),
        runtimes=runtimes,
    )
