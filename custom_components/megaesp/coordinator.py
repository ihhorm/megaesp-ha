from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    I2C_SENSORS,
    ONEWIRE_PORT,
    PORT_MODE_ANALOG,
    PORT_MODE_INPUT,
    PORT_MODE_OUTPUT,
    PORT_MODE_PWM,
)

_LOGGER = logging.getLogger(__name__)


def map_device_mode_to_port_mode(mode: int | None) -> str | None:
    if mode in (0, 4):
        return PORT_MODE_INPUT
    if mode in (1, 5):
        return PORT_MODE_OUTPUT
    if mode == 2:
        return PORT_MODE_PWM
    if mode == 3:
        return PORT_MODE_ANALOG
    return None


def parse_switch_value(raw: str) -> tuple[bool, int | None]:
    if not raw:
        return False, None
    parts = str(raw).split("/")
    state = parts[0].strip().upper() in {"ON", "1", "TRUE"}
    counter = None
    if len(parts) > 1:
        try:
            counter = int(parts[1])
        except ValueError:
            counter = None
    return state, counter


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_key_value_list(payload: str | None) -> dict[str, str] | None:
    if not payload or payload.upper() == "NA":
        return None
    data: dict[str, str] = {}
    for item in payload.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def default_port_label(idx: int) -> str:
    if idx == 10:
        return "TX"
    if idx == 11:
        return "RX"
    return f"P{idx}"


class MegaEspCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass, entry):
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.password = entry.data[CONF_PASSWORD]
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name="megaesp",
            update_interval=timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]),
        )

    def _url(self, path: str) -> str:
        return f"http://{self.host}:{self.port}{path}"

    async def _get_text(self, path: str, timeout: int = 8) -> str:
        try:
            async with asyncio.timeout(timeout):
                response = await self.session.get(self._url(path))
                response.raise_for_status()
                return (await response.text()).strip()
        except (TimeoutError, ClientError) as err:
            raise UpdateFailed(str(err)) from err

    async def _post_form(self, path: str, data: dict[str, str], timeout: int = 8) -> str:
        try:
            async with asyncio.timeout(timeout):
                response = await self.session.post(self._url(path), data=data)
                response.raise_for_status()
                return (await response.text()).strip()
        except (TimeoutError, ClientError) as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_port(self, port_idx: int, value: int) -> None:
        await self._get_text(f"/{self.password}/?cmd={port_idx}:{value}")
        await self.async_request_refresh()

    async def async_reset_counter(self, port_idx: int, value: int = 0) -> None:
        await self._get_text(f"/{self.password}/?pt={port_idx}&cnt={value}")
        await self.async_request_refresh()

    async def async_save_thermo(self, params: dict[str, str]) -> None:
        payload = {"thermoSave": "1", **params}
        await self._post_form("/sec/", payload)
        await self.async_request_refresh()

    async def async_set_ds_regulator(
        self,
        index: int,
        *,
        setpoint: float | None = None,
        hysteresis: float | None = None,
        out_port: int | None = None,
        mode: int | None = None,
        enabled: bool | None = None,
        invert: bool | None = None,
        permit_in: int | None = None,
    ) -> None:
        params: dict[str, str] = {}
        if setpoint is not None:
            params[f"ts{index}"] = f"{setpoint:.2f}"
        if hysteresis is not None:
            params[f"th{index}"] = f"{hysteresis:.2f}"
        if out_port is not None:
            params[f"to{index}"] = str(out_port)
        if mode is not None:
            params[f"tm{index}"] = str(mode)
        if enabled is not None:
            params[f"te{index}"] = "1" if enabled else "0"
        if invert is not None:
            params[f"tv{index}"] = "1" if invert else "0"
        if permit_in is not None:
            params[f"ti{index}"] = str(permit_in)
        if params:
            await self.async_save_thermo(params)

    async def async_set_pressure_regulator(
        self,
        *,
        setpoint: float | None = None,
        hysteresis: float | None = None,
        out_port: int | None = None,
        enabled: bool | None = None,
        invert: bool | None = None,
        permit_in: int | None = None,
    ) -> None:
        params: dict[str, str] = {}
        if setpoint is not None:
            params["p_set"] = f"{setpoint:.3f}"
        if hysteresis is not None:
            params["p_hyst"] = f"{hysteresis:.3f}"
        if out_port is not None:
            params["p_out"] = str(out_port)
        if enabled is not None:
            params["p_en"] = "1" if enabled else "0"
        if invert is not None:
            params["p_inv"] = "1" if invert else "0"
        if permit_in is not None:
            params["p_in"] = str(permit_in)
        if params:
            await self.async_save_thermo(params)

    async def async_set_diff_regulator(
        self,
        *,
        enabled: bool | None = None,
        invert: bool | None = None,
        permit_in: int | None = None,
        hot_kind: int | None = None,
        hot_index: int | None = None,
        tank_kind: int | None = None,
        tank_index: int | None = None,
        pump_out: int | None = None,
        dump_out: int | None = None,
        tank_min: float | None = None,
        diff_on: float | None = None,
        diff_off: float | None = None,
        overheat: float | None = None,
        overheat_hyst: float | None = None,
        freeze_on: float | None = None,
        freeze_off: float | None = None,
        freeze_tank_min: float | None = None,
        dump_mask: int | None = None,
    ) -> None:
        params: dict[str, str] = {}
        if enabled is not None:
            params["dr_en"] = "1" if enabled else "0"
        if invert is not None:
            params["dr_inv"] = "1" if invert else "0"
        if permit_in is not None:
            params["dr_in"] = str(permit_in)
        if hot_kind is not None:
            params["dr_hot_kind"] = str(hot_kind)
        if hot_index is not None:
            params["dr_hot"] = str(hot_index)
        if tank_kind is not None:
            params["dr_tank_kind"] = str(tank_kind)
        if tank_index is not None:
            params["dr_tank"] = str(tank_index)
        if pump_out is not None:
            params["dr_pump"] = str(pump_out)
        if dump_out is not None:
            params["dr_dump"] = str(dump_out)
            params["dr_dump_mask"] = "0" if dump_out == 255 else str(1 << dump_out)
        if dump_mask is not None:
            params["dr_dump_mask"] = str(dump_mask)
        if tank_min is not None:
            params["dr_tmin"] = f"{tank_min:.2f}"
        if diff_on is not None:
            params["dr_on"] = f"{diff_on:.2f}"
        if diff_off is not None:
            params["dr_off"] = f"{diff_off:.2f}"
        if overheat is not None:
            params["dr_oh"] = f"{overheat:.2f}"
        if overheat_hyst is not None:
            params["dr_ohh"] = f"{overheat_hyst:.2f}"
        if freeze_on is not None:
            params["dr_fr_on"] = f"{freeze_on:.2f}"
        if freeze_off is not None:
            params["dr_fr_off"] = f"{freeze_off:.2f}"
        if freeze_tank_min is not None:
            params["dr_fr_tmin"] = f"{freeze_tank_min:.2f}"
        if params:
            await self.async_save_thermo(params)

    async def _async_update_data(self) -> dict:
        config_raw = await self._get_text("/config.json")
        ports_raw = await self._get_text(f"/{self.password}/?cmd=all")
        onewire_raw = await self._get_text(f"/{self.password}/?pt={ONEWIRE_PORT}&cmd=get")
        sensors_status_raw = await self._get_text("/status/sensors.json")

        try:
            config = json.loads(config_raw)
        except ValueError as err:
            raise UpdateFailed(f"Invalid config.json: {err}") from err
        try:
            sensors_status = json.loads(sensors_status_raw)
        except ValueError as err:
            raise UpdateFailed(f"Invalid status/sensors.json: {err}") from err

        gpio = config.get("gpio", [])
        port_defs: list[dict] = []
        for idx, entry in enumerate(gpio):
            mode = map_device_mode_to_port_mode(int(entry.get("mode", -1)))
            if not mode:
                continue
            port_defs.append(
                {
                    "idx": idx,
                    "key": f"p{idx}",
                    "label": entry.get("name") or entry.get("gpio_label") or default_port_label(idx),
                    "mode": mode,
                    "hidden": int(entry.get("hidden", 0)) == 1,
                    "regulator": int(entry.get("regulator", 0)) == 1,
                    "sensor_type": int(entry.get("sensorType", 0) or 0),
                }
            )

        ports: dict[int, dict] = {}
        parts = ports_raw.split(";") if ports_raw else []
        for definition in port_defs:
            idx = definition["idx"]
            raw = parts[idx] if idx < len(parts) else ""
            state, counter = parse_switch_value(raw)
            ports[idx] = {
                **definition,
                "raw": raw,
                "state": state,
                "counter": counter,
                "numeric_value": parse_number(raw),
            }

        onewire: dict[str, float | None] = {}
        if onewire_raw and onewire_raw.upper() != "NA":
            for pair in onewire_raw.split(";"):
                if "=" not in pair:
                    continue
                name, value = pair.split("=", 1)
                onewire[name.strip()] = parse_number(value.strip())

        i2c: dict[str, dict] = {}
        for sensor in I2C_SENSORS:
            try:
                payload = await self._get_text(
                    f"/{self.password}/?pt={sensor['port']}&cmd=get"
                )
            except UpdateFailed as err:
                _LOGGER.debug(
                    "Skipping I2C sensor %s on P%s: %s",
                    sensor["key"],
                    sensor["port"],
                    err,
                )
                continue
            values = parse_key_value_list(payload)
            metrics: dict[str, float | str | None] = {}
            for metric in sensor["metrics"]:
                if not values or metric["field"] not in values:
                    metrics[metric["id"]] = None
                    continue
                raw_value = values[metric["field"]]
                number_value = parse_number(raw_value)
                metrics[metric["id"]] = raw_value if number_value is None else number_value
            i2c[sensor["key"]] = {
                "port": sensor["port"],
                "label": sensor["label"],
                "metrics": metrics,
            }

        ds_regulators: dict[str, dict] = {}
        for sensor in sensors_status.get("ds18b20", []):
            index = int(sensor.get("index", -1))
            if index < 0:
                continue
            reg_id = f"ds{index}"
            ds_regulators[reg_id] = {
                "id": reg_id,
                "index": index,
                "name": sensor.get("name") or f"T{index}",
                "kind": "ds",
                "type": "temp",
                "value": sensor.get("temp"),
                "set": sensor.get("thermo_set"),
                "hyst": sensor.get("thermo_hyst"),
                "mode": int(sensor.get("thermo_mode", 0) or 0),
                "out": int(sensor.get("thermo_out", 255) or 255),
                "enabled": int(sensor.get("thermo_enabled", 0) or 0) == 1,
                "invert": int(sensor.get("thermo_invert", 0) or 0) == 1,
                "permit_in": int(sensor.get("thermo_permit_in", 255) or 255),
            }

        pressure = sensors_status.get("pressure", {})
        pressure_regulator = {
            "id": "press",
            "name": "Pressure",
            "kind": "adc",
            "type": "pressure",
            "value": pressure.get("value_bar"),
            "set": pressure.get("set"),
            "hyst": pressure.get("hyst"),
            "mode": 0,
            "out": int(pressure.get("out", 255) or 255),
            "enabled": int(pressure.get("enabled", 0) or 0) == 1,
            "invert": int(pressure.get("invert", 0) or 0) == 1,
            "permit_in": int(pressure.get("permit_in", 255) or 255),
        }

        diff = sensors_status.get("diff", {})
        diff_regulator = {
            "id": "diff",
            "name": "Differential",
            "kind": "diff",
            "type": "differential",
            "enabled": int(diff.get("enabled", 0) or 0) == 1,
            "hot_kind": int(diff.get("hot_kind", 0) or 0),
            "hot": int(diff.get("hot", 255) or 255),
            "tank_kind": int(diff.get("tank_kind", 0) or 0),
            "tank": int(diff.get("tank", 255) or 255),
            "pump_out": int(diff.get("pump_out", 255) or 255),
            "dump_out": int(diff.get("dump_out", 255) or 255),
            "invert": int(diff.get("invert", 0) or 0) == 1,
            "permit_in": int(diff.get("permit_in", 255) or 255),
            "tank_min": diff.get("tank_min"),
            "diff_on": diff.get("diff_on"),
            "diff_off": diff.get("diff_off"),
            "overheat": diff.get("overheat"),
            "overheat_hyst": diff.get("overheat_hyst"),
            "freeze_on": diff.get("freeze_on"),
            "freeze_off": diff.get("freeze_off"),
            "freeze_tank_min": diff.get("freeze_tank_min"),
            "freeze_active": bool(diff.get("freeze_active", 0)),
            "overheat_active": bool(diff.get("overheat_active", 0)),
            "dump_mask": int(diff.get("dump_mask", 0) or 0),
            "hot_temp": diff.get("hot_temp"),
            "tank_temp": diff.get("tank_temp"),
            "dt": diff.get("dt"),
            "pump_state": diff.get("pump_state"),
        }

        return {
            "config": config,
            "ports": ports,
            "onewire": onewire,
            "i2c": i2c,
            "sensors_status": sensors_status,
            "ds_regulators": ds_regulators,
            "pressure_regulator": pressure_regulator,
            "diff_regulator": diff_regulator,
            "raw": {
                "config": config_raw,
                "ports": ports_raw,
                "onewire": onewire_raw,
                "sensors_status": sensors_status_raw,
            },
        }
