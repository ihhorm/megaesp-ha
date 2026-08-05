from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import MegaEspCoordinator
from .dashboard_config import (
    MegaEspDashboardConfigApiView,
    MegaEspDashboardConfigEditorView,
    MegaEspDashboardYamlApiView,
    MegaEspDashboardYamlView,
    load_dashboard_config,
    regenerate_dashboard,
    save_dashboard_config,
)

type MegaEspConfigEntry = ConfigEntry[MegaEspCoordinator]


def _slug_sensor_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _expected_unique_ids(entry: MegaEspConfigEntry, data: dict) -> set[str]:
    prefix = f"{entry.entry_id}_"
    unique_ids: set[str] = set()

    for port in data["ports"].values():
        if port["hidden"]:
            continue
        idx = int(port["idx"])
        mode = port["mode"]
        if mode == "output":
            unique_ids.add(prefix + f"switch_p{idx}")
            if port.get("regulator"):
                unique_ids.add(prefix + f"diff_reg_dump_p{idx}")
        elif mode == "input":
            unique_ids.add(prefix + f"input_p{idx}")
            unique_ids.add(prefix + f"counter_reset_p{idx}")
            unique_ids.add(prefix + f"counter_p{idx}")
        elif mode == "pwm":
            unique_ids.add(prefix + f"pwm_p{idx}")
        elif mode == "analog":
            unique_ids.add(prefix + f"analog_p{idx}")

    for regulator in data["ds_regulators"].values():
        index = int(regulator["index"])
        unique_ids.update(
            {
                prefix + f"ds_climate_{index}",
                prefix + f"ds_reg_enable_{index}",
                prefix + f"ds_reg_set_{index}",
                prefix + f"ds_reg_hyst_{index}",
                prefix + f"ds_reg_mode_{index}",
                prefix + f"ds_reg_out_{index}",
                prefix + f"ds_reg_permit_{index}",
                prefix + f"ds_reg_invert_{index}",
            }
        )

    unique_ids.update(
        {
            prefix + "pressure_reg_enable",
            prefix + "diff_reg_enable",
            prefix + "pressure_reg_set",
            prefix + "pressure_reg_hyst",
            prefix + "pressure_reg_out",
            prefix + "pressure_reg_permit",
            prefix + "pressure_reg_invert",
            prefix + "diff_reg_tank_min",
            prefix + "diff_reg_on",
            prefix + "diff_reg_off",
            prefix + "diff_reg_overheat",
            prefix + "diff_reg_overheat_hyst",
            prefix + "diff_reg_freeze_on",
            prefix + "diff_reg_freeze_off",
            prefix + "diff_reg_freeze_tank_min",
            prefix + "diff_reg_hot",
            prefix + "diff_reg_tank",
            prefix + "diff_reg_pump",
            prefix + "diff_reg_permit",
            prefix + "diff_reg_invert",
            prefix + "diff_pump_state",
            prefix + "diff_overheat_active",
            prefix + "diff_freeze_active",
            prefix + "diff_hot_temp",
            prefix + "diff_tank_temp",
            prefix + "diff_dt",
            prefix + "pressure_value",
        }
    )

    for sensor_name in data["onewire"]:
        unique_ids.add(prefix + f"onewire_{_slug_sensor_name(sensor_name)}")

    for sensor_key, sensor_data in data["i2c"].items():
        for metric_id in sensor_data["metrics"]:
            unique_ids.add(prefix + f"i2c_{sensor_key}_{metric_id}")

    return unique_ids


def _prune_stale_entities(hass: HomeAssistant, entry: MegaEspConfigEntry, data: dict) -> None:
    registry = er.async_get(hass)
    expected = _expected_unique_ids(entry, data)
    for entity_entry in list(registry.entities.values()):
        if entity_entry.config_entry_id != entry.entry_id:
            continue
        if not entity_entry.unique_id or not entity_entry.unique_id.startswith(f"{entry.entry_id}_"):
            continue
        if entity_entry.unique_id not in expected:
            registry.async_remove(entity_entry.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: MegaEspConfigEntry) -> bool:
    domain_data = hass.data.setdefault(DOMAIN, {})
    config = save_dashboard_config(hass, load_dashboard_config(hass))
    if not domain_data.get("dashboard_config_views_registered"):
        hass.http.register_view(MegaEspDashboardConfigApiView())
        hass.http.register_view(MegaEspDashboardConfigEditorView())
        hass.http.register_view(MegaEspDashboardYamlApiView())
        hass.http.register_view(MegaEspDashboardYamlView())
        domain_data["dashboard_config_views_registered"] = True
        regenerate_dashboard(hass, config)

    coordinator = MegaEspCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    _prune_stale_entities(hass, entry, coordinator.data)

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
    regenerate_dashboard(hass, config)

    async def _sync_dashboard_and_entities() -> None:
        _prune_stale_entities(hass, entry, coordinator.data)
        regenerate_dashboard(hass, config)

    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: hass.async_create_task(_sync_dashboard_and_entities())
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MegaEspConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
