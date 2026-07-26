"""Frontend registration for the Vehicle Maintenance dashboard card."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.lovelace.const import MODE_STORAGE
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_BASE_URL = "/vehicle-maintenance"
CARD_URL = f"{CARD_BASE_URL}/vehicle-maint-bootstrap.js"
LEGACY_CARD_URL = f"{CARD_BASE_URL}/vehicle-maint-card.js"
CARD_VERSION = "0.2.2"
CARD_RESOURCE_URL = f"{CARD_URL}?v={CARD_VERSION}"


def _base_url(url: str) -> str:
    """Return a resource URL without its cache-busting query string."""
    return url.split("?", 1)[0]


def _lovelace_mode_and_resources(hass: HomeAssistant):
    """Return Lovelace resource mode and collection across supported HA versions."""
    lovelace = hass.data.get(LOVELACE_DOMAIN)
    if lovelace is None:
        return None, None

    # Home Assistant 2024.x used a dictionary. 2025.x migrated Lovelace data to
    # a dataclass with ``mode``. Newer Home Assistant uses ``resource_mode``.
    if isinstance(lovelace, dict):
        mode = lovelace.get("resource_mode", lovelace.get("mode"))
        resources = lovelace.get("resources")
    else:
        mode = getattr(lovelace, "resource_mode", None)
        if mode is None:
            mode = getattr(lovelace, "mode", None)
        resources = getattr(lovelace, "resources", None)

    return mode, resources


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> bool:
    """Create or update the module in Lovelace storage mode."""
    mode, resources = _lovelace_mode_and_resources(hass)
    if mode != MODE_STORAGE or resources is None:
        return False

    await resources.async_get_info()  # Ensure the storage collection is loaded.

    for item in resources.async_items() or []:
        if _base_url(str(item.get("url", ""))) not in {CARD_URL, LEGACY_CARD_URL}:
            continue

        if item.get("url") != CARD_RESOURCE_URL or item.get("type") != "module":
            await resources.async_update_item(
                item["id"],
                {"url": CARD_RESOURCE_URL, "res_type": "module"},
            )
        return True

    await resources.async_create_item(
        {"url": CARD_RESOURCE_URL, "res_type": "module"}
    )
    return True


async def async_register_card_frontend(hass: HomeAssistant) -> None:
    """Serve the card and make it available to every Home Assistant client."""
    card_directory = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_BASE_URL, str(card_directory), False)]
    )

    try:
        if await _async_ensure_lovelace_resource(hass):
            return
    except Exception:
        _LOGGER.exception(
            "Failed to register Vehicle Maintenance as a Lovelace resource; "
            "falling back to Home Assistant frontend module injection"
        )

    # YAML resource mode cannot be changed safely from an integration. Keep the
    # legacy frontend registration as a compatibility fallback for those users.
    add_extra_js_url(hass, CARD_RESOURCE_URL)
