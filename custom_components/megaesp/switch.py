from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PORT_MODE_OUTPUT
from .entity import MegaEspEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known_ports: set[int] = set()
    known_keys: set[str] = set()

    def build_entities() -> list[SwitchEntity]:
        entities: list[SwitchEntity] = []
        for port in coordinator.data["ports"].values():
            if port["hidden"] or port["mode"] != PORT_MODE_OUTPUT:
                continue
            if port["idx"] in known_ports:
                continue
            known_ports.add(port["idx"])
            entities.append(MegaEspPortSwitch(coordinator, entry, port["idx"]))

        for regulator in coordinator.data["ds_regulators"].values():
            enabled_key = f"ds_enable_{regulator['index']}"
            invert_key = f"ds_invert_{regulator['index']}"
            if enabled_key not in known_keys:
                known_keys.add(enabled_key)
                entities.append(MegaEspDsRegulatorEnabledSwitch(coordinator, entry, regulator["index"]))
            if invert_key not in known_keys:
                known_keys.add(invert_key)
                entities.append(MegaEspDsRegulatorInvertSwitch(coordinator, entry, regulator["index"]))

        if "pressure_enable" not in known_keys:
            known_keys.add("pressure_enable")
            entities.append(MegaEspPressureRegulatorEnabledSwitch(coordinator, entry))
        if "pressure_invert" not in known_keys:
            known_keys.add("pressure_invert")
            entities.append(MegaEspPressureRegulatorInvertSwitch(coordinator, entry))
        if "diff_enable" not in known_keys:
            known_keys.add("diff_enable")
            entities.append(MegaEspDiffRegulatorEnabledSwitch(coordinator, entry))
        if "diff_invert" not in known_keys:
            known_keys.add("diff_invert")
            entities.append(MegaEspDiffRegulatorInvertSwitch(coordinator, entry))

        for port in coordinator.data["ports"].values():
            if port["hidden"] or port["mode"] != PORT_MODE_OUTPUT or not port.get("regulator"):
                continue
            key = f"diff_dump_{port['idx']}"
            if key in known_keys:
                continue
            known_keys.add(key)
            entities.append(MegaEspDiffDumpPortSwitch(coordinator, entry, port["idx"]))
        return entities

    entities = build_entities()
    if entities:
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(lambda: async_add_entities(build_entities())))


class MegaEspPortSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry, port_idx: int) -> None:
        super().__init__(coordinator, entry, f"switch_p{port_idx}")
        self._port_idx = port_idx
        self._attr_name = coordinator.data["ports"][port_idx]["label"]

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["ports"][self._port_idx]["state"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_port(self._port_idx, 1)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_port(self._port_idx, 0)


class MegaEspDsRegulatorEnabledSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_reg_enable_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = f"{name} Regulator Enabled"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["ds_regulators"][f"ds{self._index}"]["enabled"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, enabled=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, enabled=False)


class MegaEspDsRegulatorInvertSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_reg_invert_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = f"{name} Regulator Invert"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["ds_regulators"][f"ds{self._index}"]["invert"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, invert=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, invert=False)


class MegaEspPressureRegulatorEnabledSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pressure_reg_enable")
        self._attr_name = "Pressure Regulator Enabled"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["pressure_regulator"]["enabled"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_pressure_regulator(enabled=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_pressure_regulator(enabled=False)


class MegaEspPressureRegulatorInvertSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pressure_reg_invert")
        self._attr_name = "Pressure Regulator Invert"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["pressure_regulator"]["invert"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_pressure_regulator(invert=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_pressure_regulator(invert=False)


class MegaEspDiffRegulatorEnabledSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_enable")
        self._attr_name = "Differential Regulator Enabled"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["diff_regulator"]["enabled"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_diff_regulator(enabled=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_diff_regulator(enabled=False)


class MegaEspDiffRegulatorInvertSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "diff_reg_invert")
        self._attr_name = "Differential Regulator Invert"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["diff_regulator"]["invert"])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_diff_regulator(invert=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_diff_regulator(invert=False)


class MegaEspDiffDumpPortSwitch(MegaEspEntity, SwitchEntity):
    def __init__(self, coordinator, entry, port_idx: int) -> None:
        super().__init__(coordinator, entry, f"diff_reg_dump_p{port_idx}")
        self._port_idx = port_idx
        label = coordinator.data["ports"][port_idx]["label"]
        self._attr_name = f"Differential Dump {label}"

    @property
    def is_on(self) -> bool:
        mask = int(self.coordinator.data["diff_regulator"]["dump_mask"] or 0)
        return bool(mask & (1 << self._port_idx))

    async def async_turn_on(self, **kwargs) -> None:
        mask = int(self.coordinator.data["diff_regulator"]["dump_mask"] or 0)
        await self.coordinator.async_set_diff_regulator(dump_mask=mask | (1 << self._port_idx))

    async def async_turn_off(self, **kwargs) -> None:
        mask = int(self.coordinator.data["diff_regulator"]["dump_mask"] or 0)
        await self.coordinator.async_set_diff_regulator(dump_mask=mask & ~(1 << self._port_idx))
