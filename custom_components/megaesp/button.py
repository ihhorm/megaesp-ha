from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PORT_MODE_INPUT
from .entity import MegaEspEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known_ports: set[int] = set()

    def build_entities() -> list[MegaEspCounterResetButton]:
        entities: list[MegaEspCounterResetButton] = []
        for port in coordinator.data["ports"].values():
            if port["hidden"] or port["mode"] != PORT_MODE_INPUT:
                continue
            if port["idx"] in known_ports:
                continue
            known_ports.add(port["idx"])
            entities.append(MegaEspCounterResetButton(coordinator, entry, port["idx"]))
        return entities

    entities = build_entities()
    if entities:
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(lambda: async_add_entities(build_entities())))


class MegaEspCounterResetButton(MegaEspEntity, ButtonEntity):
    def __init__(self, coordinator, entry, port_idx: int) -> None:
        super().__init__(coordinator, entry, f"counter_reset_p{port_idx}")
        self._port_idx = port_idx
        self._attr_name = f"{coordinator.data['ports'][port_idx]['label']} Counter Reset"

    async def async_press(self) -> None:
        await self.coordinator.async_reset_counter(self._port_idx, 0)
