"""Config flow for the MXW01 add-on bridge."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_BRIDGE_URL, DEFAULT_BRIDGE_URL, DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up the integration using the internal add-on URL."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            user_input[CONF_BRIDGE_URL] = user_input[CONF_BRIDGE_URL].rstrip("/")
            await self.async_set_unique_id("mxw01_addon_bridge")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="MXW01 Bluetooth Printer", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_BRIDGE_URL, default=DEFAULT_BRIDGE_URL): str}),
        )
