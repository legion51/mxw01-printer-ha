"""Home Assistant service action for the MXW01 add-on."""
from __future__ import annotations

import asyncio
from aiohttp import ClientError
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_BRIDGE_URL, DOMAIN, SERVICE_PRINT

SERVICE_SCHEMA = vol.Schema({
    vol.Optional("title"): cv.string,
    vol.Optional("text"): cv.string,
    vol.Optional("centered", default=False): cv.boolean,
    vol.Optional("separator", default=True): cv.boolean,
    vol.Optional("qr_data"): cv.string,
    vol.Optional("image_url"): cv.string,
    vol.Optional("font_size", default=20): vol.All(vol.Coerce(int), vol.Range(min=10, max=40)),
    vol.Optional("qr_size", default=3): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
    vol.Optional("image_scale", default=100): vol.All(vol.Coerce(int), vol.Range(min=20, max=200)),
})


def _make_markup(data: dict) -> str:
    lines: list[str] = []
    if title := data.get("title", "").strip():
        lines.append(f"# {title}")
    if content := data.get("text", "").strip():
        prefix = "[C]" if data["centered"] else ""
        lines.extend(f"{prefix}{line}" if line.strip() else "" for line in content.splitlines())
    if data["separator"] and (data.get("qr_data") or data.get("image_url")):
        lines.append("---")
    if qr_data := data.get("qr_data", "").strip():
        lines.append(f"[QR:{qr_data}]")
    if image_url := data.get("image_url", "").strip():
        lines.append(f"[IMG:{image_url}]")
    if not any(line.strip() for line in lines):
        raise HomeAssistantError("Укажите хотя бы заголовок, текст, QR-код или изображение")
    return "\n".join(lines)


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data[CONF_BRIDGE_URL]

    async def async_print(call: ServiceCall) -> None:
        bridge_url = next(iter(hass.data[DOMAIN].values()))
        body = dict(call.data)
        body["markdown"] = _make_markup(body)
        try:
            async with async_get_clientsession(hass).post(f"{bridge_url}/api/print", json=body, timeout=90) as response:
                if response.status >= 400:
                    message = await response.json(content_type=None)
                    raise HomeAssistantError(message.get("detail", f"Ошибка add-on: HTTP {response.status}"))
        except (ClientError, asyncio.TimeoutError) as error:
            raise HomeAssistantError(
                f"Не удалось связаться с add-on по адресу {bridge_url}. "
                "Откройте Web UI add-on, скопируйте «Адрес для integration» и "
                "создайте integration заново с этим адресом."
            ) from error

    if not hass.services.has_service(DOMAIN, SERVICE_PRINT):
        hass.services.async_register(DOMAIN, SERVICE_PRINT, async_print, schema=SERVICE_SCHEMA)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_PRINT)
    return True
