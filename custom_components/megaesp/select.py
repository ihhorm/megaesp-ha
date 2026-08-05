from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import MegaEspEntity


def _output_ports(coordinator) -> list[dict]:
    flagged = [
        port
        for port in coordinator.data["ports"].values()
        if not port["hidden"] and port["mode"] == "output" and port.get("regulator")
    ]
    if flagged:
        return flagged
    return [
        port
        for port in coordinator.data["ports"].values()
        if not port["hidden"] and port["mode"] == "output"
    ]


def _output_options(coordinator) -> list[str]:
    options = ["—"]
    for port in _output_ports(coordinator):
        options.append(port["label"])
    return options


def _label_to_port(coordinator, label: str) -> int:
    for port in _output_ports(coordinator):
        if port["label"] == label:
            return int(port["idx"])
    return 255


def _port_to_label(coordinator, port_idx: int) -> str:
    if port_idx == 255:
        return "—"
    port = coordinator.data["ports"].get(port_idx)
    if not port:
        return "—"
    return port["label"]


def _input_ports(coordinator) -> list[dict]:
    return [
        port
        for port in coordinator.data["ports"].values()
        if not port["hidden"] and port["mode"] == "input"
    ]


def _input_options(coordinator) -> list[str]:
    options = ["—"]
    for port in _input_ports(coordinator):
        options.append(port["label"])
    return options


def _label_to_input_port(coordinator, label: str) -> int:
    for port in _input_ports(coordinator):
        if port["label"] == label:
            return int(port["idx"])
    return 255


def _diff_sensor_options(coordinator) -> list[str]:
    options = ["—"]
    for regulator in coordinator.data["ds_regulators"].values():
        options.append(f"DS: {regulator['name']}")
    for sensor_key, sensor_data in coordinator.data["i2c"].items():
        temperature = sensor_data["metrics"].get("temperature")
        if temperature is None:
            continue
        options.append(f"I2C: {sensor_data['label']}")
    return options


def _diff_sensor_to_option(coordinator, kind: int, index: int) -> str:
    if index == 255:
        return "—"
    if kind == 0:
        reg = coordinator.data["ds_regulators"].get(f"ds{index}")
        return f"DS: {reg['name']}" if reg else "—"
    if kind == 1:
        i2c_with_temp = [
            sensor_data["label"]
            for sensor_data in coordinator.data["i2c"].values()
            if sensor_data["metrics"].get("temperature") is not None
        ]
        if 0 <= index < len(i2c_with_temp):
            return f"I2C: {i2c_with_temp[index]}"
    return "—"


def _option_to_diff_sensor(coordinator, option: str) -> tuple[int, int]:
    if option == "—":
        return 0, 255
    if option.startswith("DS: "):
        name = option[4:]
        for regulator in coordinator.data["ds_regulators"].values():
            if regulator["name"] == name:
                return 0, int(regulator["index"])
    if option.startswith("I2C: "):
        label = option[5:]
        i2c_with_temp = [
            sensor_data["label"]
            for sensor_data in coordinator.data["i2c"].values()
            if sensor_data["metrics"].get("temperature") is not None
        ]
        for index, current_label in enumerate(i2c_with_temp):
            if current_label == label:
                return 1, index
    return 0, 255


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known_keys: set[str] = set()

    def build_entities() -> list[SelectEntity]:
        entities: list[SelectEntity] = []

        for regulator in coordinator.data["ds_regulators"].values():
            mode_key = f"ds_mode_{regulator['index']}"
            out_key = f"ds_out_{regulator['index']}"
            permit_key = f"ds_permit_{regulator['index']}"
            if mode_key not in known_keys:
                known_keys.add(mode_key)
                entities.append(MegaEspDsRegulatorModeSelect(coordinator, entry, regulator["index"]))
            if out_key not in known_keys:
                known_keys.add(out_key)
                entities.append(MegaEspDsRegulatorOutputSelect(coordinator, entry, regulator["index"]))
            if permit_key not in known_keys:
                known_keys.add(permit_key)
                entities.append(MegaEspDsRegulatorPermitInputSelect(coordinator, entry, regulator["index"]))

        if "pressure_out" not in known_keys:
            known_keys.add("pressure_out")
            entities.append(MegaEspPressureRegulatorOutputSelect(coordinator, entry))
        if "pressure_permit" not in known_keys:
            known_keys.add("pressure_permit")
            entities.append(MegaEspPressureRegulatorPermitInputSelect(coordinator, entry))
        diff_keys = (
            ("diff_hot", MegaEspDiffRegulatorHotSensorSelect),
            ("diff_tank", MegaEspDiffRegulatorTankSensorSelect),
            ("diff_pump", MegaEspDiffRegulatorPumpOutputSelect),
            ("diff_permit", MegaEspDiffRegulatorPermitInputSelect),
        )
        for key, cls in diff_keys:
            if key in known_keys:
                continue
            known_keys.add(key)
            entities.append(cls(coordinator, entry))

        return entities

    entities = build_entities()
    if entities:
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(lambda: async_add_entities(build_entities())))


class MegaEspDsRegulatorModeSelect(MegaEspEntity, SelectEntity):
    _attr_options = ["Heat", "Cool"]

    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_reg_mode_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = f"{name} Regulator Mode"

    @property
    def current_option(self) -> str:
        mode = int(self.coordinator.data["ds_regulators"][f"ds{self._index}"]["mode"])
        return "Cool" if mode == 1 else "Heat"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_ds_regulator(
            self._index, mode=1 if option == "Cool" else 0
        )


class MegaEspDsRegulatorOutputSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_reg_out_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = f"{name} Regulator Output"

    @property
    def options(self) -> list[str]:
        return _output_options(self.coordinator)

    @property
    def current_option(self) -> str:
        port_idx = int(self.coordinator.data["ds_regulators"][f"ds{self._index}"]["out"])
        return _port_to_label(self.coordinator, port_idx)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_ds_regulator(
            self._index, out_port=_label_to_port(self.coordinator, option)
        )


class MegaEspDsRegulatorPermitInputSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_reg_permit_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = f"{name} Regulator Permit Input"

    @property
    def options(self) -> list[str]:
        return _input_options(self.coordinator)

    @property
    def current_option(self) -> str:
        port_idx = int(self.coordinator.data["ds_regulators"][f"ds{self._index}"]["permit_in"])
        return _port_to_label(self.coordinator, port_idx)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_ds_regulator(
            self._index, permit_in=_label_to_input_port(self.coordinator, option)
        )


class MegaEspPressureRegulatorOutputSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pressure_reg_out")
        self._attr_name = "Pressure Regulator Output"

    @property
    def options(self) -> list[str]:
        return _output_options(self.coordinator)

    @property
    def current_option(self) -> str:
        port_idx = int(self.coordinator.data["pressure_regulator"]["out"])
        return _port_to_label(self.coordinator, port_idx)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_pressure_regulator(
            out_port=_label_to_port(self.coordinator, option)
        )


class MegaEspPressureRegulatorPermitInputSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pressure_reg_permit")
        self._attr_name = "Pressure Regulator Permit Input"

    @property
    def options(self) -> list[str]:
        return _input_options(self.coordinator)

    @property
    def current_option(self) -> str:
        port_idx = int(self.coordinator.data["pressure_regulator"]["permit_in"])
        return _port_to_label(self.coordinator, port_idx)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_pressure_regulator(
            permit_in=_label_to_input_port(self.coordinator, option)
        )


class MegaEspDiffRegulatorHotSensorSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_hot")
        self._attr_name = "Differential Regulator Hot Sensor"

    @property
    def options(self) -> list[str]:
        return _diff_sensor_options(self.coordinator)

    @property
    def current_option(self) -> str:
        reg = self.coordinator.data["diff_regulator"]
        return _diff_sensor_to_option(self.coordinator, reg["hot_kind"], reg["hot"])

    async def async_select_option(self, option: str) -> None:
        kind, index = _option_to_diff_sensor(self.coordinator, option)
        await self.coordinator.async_set_diff_regulator(hot_kind=kind, hot_index=index)


class MegaEspDiffRegulatorTankSensorSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_tank")
        self._attr_name = "Differential Regulator Tank Sensor"

    @property
    def options(self) -> list[str]:
        return _diff_sensor_options(self.coordinator)

    @property
    def current_option(self) -> str:
        reg = self.coordinator.data["diff_regulator"]
        return _diff_sensor_to_option(self.coordinator, reg["tank_kind"], reg["tank"])

    async def async_select_option(self, option: str) -> None:
        kind, index = _option_to_diff_sensor(self.coordinator, option)
        await self.coordinator.async_set_diff_regulator(tank_kind=kind, tank_index=index)


class MegaEspDiffRegulatorPumpOutputSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_pump")
        self._attr_name = "Differential Regulator Pump Output"

    @property
    def options(self) -> list[str]:
        return _output_options(self.coordinator)

    @property
    def current_option(self) -> str:
        return _port_to_label(
            self.coordinator, int(self.coordinator.data["diff_regulator"]["pump_out"])
        )

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_diff_regulator(
            pump_out=_label_to_port(self.coordinator, option)
        )


class MegaEspDiffRegulatorPermitInputSelect(MegaEspEntity, SelectEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_permit")
        self._attr_name = "Differential Regulator Permit Input"

    @property
    def options(self) -> list[str]:
        return _input_options(self.coordinator)

    @property
    def current_option(self) -> str:
        return _port_to_label(
            self.coordinator, int(self.coordinator.data["diff_regulator"]["permit_in"])
        )

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_diff_regulator(
            permit_in=_label_to_input_port(self.coordinator, option)
        )
