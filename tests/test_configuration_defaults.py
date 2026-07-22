"""Regression checks for user-facing integration defaults."""

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
CONST = ROOT / "custom_components/vehicle_maintenance/const.py"
spec = importlib.util.spec_from_file_location("vehicle_maintenance_const", CONST)
const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const)


def test_new_vehicles_select_the_complete_catalog() -> None:
    assert const.DEFAULT_SERVICES == list(const.SERVICE_CATALOG)


def test_manifest_classifies_each_config_entry_as_a_device() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/vehicle_maintenance/manifest.json").read_text()
    )

    assert manifest["integration_type"] == "device"


def test_release_and_frontend_cache_versions_stay_aligned() -> None:
    component = ROOT / "custom_components/vehicle_maintenance"
    manifest = json.loads((component / "manifest.json").read_text())
    integration_source = (component / "__init__.py").read_text()
    card_source = (component / "www/vehicle-maint-card.js").read_text()

    version = manifest["version"]
    assert f'?v={version}"' in integration_source
    assert f'CARD_VERSION = "{version}"' in card_source


def test_service_actions_never_offer_not_set() -> None:
    services = (
        ROOT / "custom_components/vehicle_maintenance/services.yaml"
    ).read_text()

    assert "label: Not set" not in services
    assert "label: Never performed" in services
