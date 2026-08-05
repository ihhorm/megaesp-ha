from __future__ import annotations

from copy import deepcopy

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL

TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(hass, entry) -> dict:
    coordinator = entry.runtime_data
    diagnostics = {
        "entry": dict(entry.data),
        "coordinator_data": deepcopy(coordinator.data),
    }
    diagnostics["entry"] = async_redact_data(diagnostics["entry"], TO_REDACT)
    return diagnostics
