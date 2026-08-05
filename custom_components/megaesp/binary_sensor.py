from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PORT_MODE_INPUT
from .entity import MegaEspEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known_ports: set[int] = set()
    known_keys: set[str] = set()

    def build_entities() -> list[BinarySensorEntity]:
        entities: list[BinarySensorEntity] = []
        for port in coordinator.data["ports"].values():
            if port["hidden"] or port["mode"] != PORT_MODE_INPUT:
                continue
            if port["idx"] in known_ports:
                continue
            known_ports.add(port["idx"])
            entities.append(MegaEspInputBinarySensor(coordinator, entry, port["idx"]))

        diff_entities = (
            ("diff_pump_state", "pump_state", "Differential Pump Active"),
            ("diff_overheat_active", "overheat_active", "Differential Overheat Active"),
            ("diff_freeze_active", "freeze_active", "Differential Freeze Active"),
        )
        for key, field, name in diff_entities:
            if key in known_keys:
                continue
            known_keys.add(key)
            entities.append(MegaEspDiffBinarySensor(coordinator, entry, key, field, name))
        return entities

    entities = build_entities()
    if entities:
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(lambda: async_add_entities(build_entities())))


class MegaEspInputBinarySensor(MegaEspEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, port_idx: int) -> None:
        super().__init__(coordinator, entry, f"input_p{port_idx}")
        self._port_idx = port_idx
        self._attr_name = coordinator.data["ports"][port_idx]["label"]

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["ports"][self._port_idx]["state"])


class MegaEspDiffBinarySensor(MegaEspEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, unique_key: str, field: str, name: str) -> None:
        super().__init__(coordinator, entry, unique_key)
        self._field = field
        self._attr_name = name

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["diff_regulator"].get(self._field))
