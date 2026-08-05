from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PORT_MODE_PWM
from .entity import MegaEspEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known_ports: set[int] = set()
    known_keys: set[str] = set()

    def build_entities() -> list[NumberEntity]:
        entities: list[NumberEntity] = []
        for port in coordinator.data["ports"].values():
            if port["hidden"] or port["mode"] != PORT_MODE_PWM:
                continue
            if port["idx"] in known_ports:
                continue
            known_ports.add(port["idx"])
            entities.append(MegaEspPwmNumber(coordinator, entry, port["idx"]))

        for regulator in coordinator.data["ds_regulators"].values():
            set_key = f"ds_set_{regulator['index']}"
            hyst_key = f"ds_hyst_{regulator['index']}"
            if set_key not in known_keys:
                known_keys.add(set_key)
                entities.append(MegaEspDsSetpointNumber(coordinator, entry, regulator["index"]))
            if hyst_key not in known_keys:
                known_keys.add(hyst_key)
                entities.append(MegaEspDsHysteresisNumber(coordinator, entry, regulator["index"]))

        if "pressure_set" not in known_keys:
            known_keys.add("pressure_set")
            entities.append(MegaEspPressureSetpointNumber(coordinator, entry))
        if "pressure_hyst" not in known_keys:
            known_keys.add("pressure_hyst")
            entities.append(MegaEspPressureHysteresisNumber(coordinator, entry))

        diff_numbers = (
            ("diff_tank_min", MegaEspDiffTankMinNumber),
            ("diff_on", MegaEspDiffOnNumber),
            ("diff_off", MegaEspDiffOffNumber),
            ("diff_overheat", MegaEspDiffOverheatNumber),
            ("diff_overheat_hyst", MegaEspDiffOverheatHystNumber),
            ("diff_freeze_on", MegaEspDiffFreezeOnNumber),
            ("diff_freeze_off", MegaEspDiffFreezeOffNumber),
            ("diff_freeze_tank_min", MegaEspDiffFreezeTankMinNumber),
        )
        for key, cls in diff_numbers:
            if key in known_keys:
                continue
            known_keys.add(key)
            entities.append(cls(coordinator, entry))

        return entities

    entities = build_entities()
    if entities:
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(lambda: async_add_entities(build_entities())))


class MegaEspPwmNumber(MegaEspEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_native_step = 1

    def __init__(self, coordinator, entry, port_idx: int) -> None:
        super().__init__(coordinator, entry, f"pwm_p{port_idx}")
        self._port_idx = port_idx
        self._attr_name = f"{coordinator.data['ports'][port_idx]['label']} PWM"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["ports"][self._port_idx]["numeric_value"]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_port(self._port_idx, int(value))


class _MegaEspRegulatorNumber(MegaEspEntity, NumberEntity):
    def __init__(self, coordinator, entry, unique_key: str) -> None:
        super().__init__(coordinator, entry, unique_key)


class MegaEspDsSetpointNumber(_MegaEspRegulatorNumber):
    _attr_native_min_value = -55
    _attr_native_max_value = 125
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "°C"

    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_reg_set_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = f"{name} Regulator Setpoint"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["ds_regulators"][f"ds{self._index}"]["set"]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, setpoint=value)


class MegaEspDsHysteresisNumber(_MegaEspRegulatorNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 50
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "°C"

    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_reg_hyst_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = f"{name} Regulator Hysteresis"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["ds_regulators"][f"ds{self._index}"]["hyst"]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, hysteresis=value)


class MegaEspPressureSetpointNumber(_MegaEspRegulatorNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 6.895
    _attr_native_step = 0.001
    _attr_native_unit_of_measurement = "bar"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pressure_reg_set")
        self._attr_name = "Pressure Regulator Setpoint"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["pressure_regulator"]["set"]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_pressure_regulator(setpoint=value)


class MegaEspPressureHysteresisNumber(_MegaEspRegulatorNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 5
    _attr_native_step = 0.001
    _attr_native_unit_of_measurement = "bar"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pressure_reg_hyst")
        self._attr_name = "Pressure Regulator Hysteresis"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["pressure_regulator"]["hyst"]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_pressure_regulator(hysteresis=value)


class _MegaEspDiffNumber(_MegaEspRegulatorNumber):
    _attr_native_unit_of_measurement = "°C"
    _field: str
    _name: str

    def __init__(self, coordinator, entry, unique_key: str) -> None:
        super().__init__(coordinator, entry, unique_key)
        self._attr_name = self._name

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["diff_regulator"][self._field]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_diff_regulator(**{self._field: value})


class MegaEspDiffTankMinNumber(_MegaEspDiffNumber):
    _attr_native_min_value = -55
    _attr_native_max_value = 125
    _attr_native_step = 0.1
    _field = "tank_min"
    _name = "Differential Regulator Tank Minimum"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_tank_min")


class MegaEspDiffOnNumber(_MegaEspDiffNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 50
    _attr_native_step = 0.1
    _field = "diff_on"
    _name = "Differential Regulator Delta On"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_on")


class MegaEspDiffOffNumber(_MegaEspDiffNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 50
    _attr_native_step = 0.1
    _field = "diff_off"
    _name = "Differential Regulator Delta Off"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_off")


class MegaEspDiffOverheatNumber(_MegaEspDiffNumber):
    _attr_native_min_value = -55
    _attr_native_max_value = 125
    _attr_native_step = 0.1
    _field = "overheat"
    _name = "Differential Regulator Overheat"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_overheat")


class MegaEspDiffOverheatHystNumber(_MegaEspDiffNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 50
    _attr_native_step = 0.1
    _field = "overheat_hyst"
    _name = "Differential Regulator Overheat Hysteresis"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_overheat_hyst")


class MegaEspDiffFreezeOnNumber(_MegaEspDiffNumber):
    _attr_native_min_value = -55
    _attr_native_max_value = 125
    _attr_native_step = 0.1
    _field = "freeze_on"
    _name = "Differential Regulator Freeze On"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_freeze_on")


class MegaEspDiffFreezeOffNumber(_MegaEspDiffNumber):
    _attr_native_min_value = -55
    _attr_native_max_value = 125
    _attr_native_step = 0.1
    _field = "freeze_off"
    _name = "Differential Regulator Freeze Off"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_freeze_off")


class MegaEspDiffFreezeTankMinNumber(_MegaEspDiffNumber):
    _attr_native_min_value = -55
    _attr_native_max_value = 125
    _attr_native_step = 0.1
    _field = "freeze_tank_min"
    _name = "Differential Regulator Freeze Tank Minimum"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_freeze_tank_min")
