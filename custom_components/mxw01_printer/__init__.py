"""MXW01 custom integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_BRIDGE_URL, DOMAIN

SERVICE_PRINT = "print"
SERVICE_SCHEMA = vol.Schema({
    vol.Required("markdown"): cv.string,
    vol.Optional("font_size", default=20): vol.All(vol.Coerce(int), vol.Range(min=10, max=40)),
    vol.Optional("qr_size", default=3): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
    vol.Optional("image_scale", default=100): vol.All(vol.Coerce(int), vol.Range(min=20, max=200)),
    vol.Optional("device_address"): cv.string,
})


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data[CONF_BRIDGE_URL].rstrip("/")

    async def async_print(call: ServiceCall) -> None:
        # The first configured bridge owns the service; multiple printer support can
        # be added later by selecting a config-entry target.
        bridge_url = next(iter(hass.data[DOMAIN].values()))
        async with async_get_clientsession(hass).post(
            f"{bridge_url}/print", json=dict(call.data), timeout=90
        ) as response:
            if response.status >= 400:
                payload = await response.json(content_type=None)
                raise RuntimeError(payload.get("detail", f"MXW01 bridge returned HTTP {response.status}"))

    if not hass.services.has_service(DOMAIN, SERVICE_PRINT):
        hass.services.async_register(DOMAIN, SERVICE_PRINT, async_print, schema=SERVICE_SCHEMA)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_PRINT)
    return True
