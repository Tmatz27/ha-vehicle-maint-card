"""Static regression checks for the bundled dashboard-card bootstrap."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
BOOTSTRAP = (
    ROOT
    / "custom_components/vehicle_maintenance/www/vehicle-maint-bootstrap.js"
).read_text()


def test_completed_milestones_are_removed_from_card_views() -> None:
    assert "completedMilestone" in BOOTSTRAP
    assert "all.filter((entity) => !completedMilestone(entity))" in BOOTSTRAP


def test_service_lookup_is_cached_per_vehicle() -> None:
    assert "__vehicleMaintServices" in BOOTSTRAP
    assert "this.serviceEntityIds = all.map" in BOOTSTRAP
    assert "this.__vehicleMaintServices = { entryId, visible }" in BOOTSTRAP


def test_card_and_editor_styles_are_scoped() -> None:
    assert "scopeRuleList" in BOOTSTRAP
    assert 'scopeStyles(this, "vehicle-maint-card")' in BOOTSTRAP
    assert 'scopeStyles(this, "vehicle-maint-card-editor")' in BOOTSTRAP


def test_card_controls_receive_instance_unique_ids() -> None:
    assert "namespaceIds" in BOOTSTRAP
    assert 'namespaceIds(this, "vm-card")' in BOOTSTRAP
    assert 'namespaceIds(this, "vm-editor")' in BOOTSTRAP


def test_editor_avoids_unrelated_hass_rerenders() -> None:
    assert "vehicleSignature" in BOOTSTRAP
    assert "signature !== this._vehicleSignature" in BOOTSTRAP
    assert "if (shouldRender) renderWhenIdle.call(this);" in BOOTSTRAP


def test_editor_avoids_repeated_set_config_rerenders() -> None:
    assert "normalizeEditorConfig" in BOOTSTRAP
    assert "editorConfigSignature" in BOOTSTRAP
    assert "Editor.prototype.setConfig = function setConfig(config)" in BOOTSTRAP
    assert "previousSignature !== nextSignature" in BOOTSTRAP


def test_editor_defers_required_render_while_control_has_focus() -> None:
    assert "installFocusGuard" in BOOTSTRAP
    assert "this.contains(document.activeElement)" in BOOTSTRAP
    assert "this.__vehicleMaintRenderPending = true" in BOOTSTRAP
    assert "queueMicrotask" in BOOTSTRAP
