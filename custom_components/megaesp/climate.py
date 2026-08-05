from __future__ import annotations

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import MegaEspEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known_keys: set[str] = set()

    def build_entities() -> list[ClimateEntity]:
        entities: list[ClimateEntity] = []
        for regulator in coordinator.data["ds_regulators"].values():
            key = f"ds_climate_{regulator['index']}"
            if key in known_keys:
                continue
            known_keys.add(key)
            entities.append(MegaEspDsRegulatorClimate(coordinator, entry, regulator["index"]))
        return entities

    entities = build_entities()
    if entities:
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(lambda: async_add_entities(build_entities())))


class MegaEspDsRegulatorClimate(MegaEspEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.1
    _attr_min_temp = -55.0
    _attr_max_temp = 125.0
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]

    def __init__(self, coordinator, entry, index: int) -> None:
        super().__init__(coordinator, entry, f"ds_climate_{index}")
        self._index = index
        name = coordinator.data["ds_regulators"][f"ds{index}"]["name"]
        self._attr_name = name

    @property
    def _reg(self) -> dict:
        return self.coordinator.data["ds_regulators"][f"ds{self._index}"]

    @property
    def current_temperature(self) -> float | None:
        return self._reg.get("value")

    @property
    def target_temperature(self) -> float | None:
        return self._reg.get("set")

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._reg.get("enabled"):
            return HVACMode.OFF
        return HVACMode.COOL if int(self._reg.get("mode") or 0) == 1 else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        current = self.current_temperature
        target = self.target_temperature
        hyst = self._reg.get("hyst")
        if not self._reg.get("enabled"):
            return HVACAction.OFF
        if current is None or target is None or hyst is None:
            return HVACAction.IDLE
        if int(self._reg.get("mode") or 0) == 1:
            return HVACAction.COOLING if current > (target + hyst) else HVACAction.IDLE
        return HVACAction.HEATING if current < (target - hyst) else HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "hysteresis": self._reg.get("hyst"),
            "output_port": self._reg.get("out"),
            "permit_input": self._reg.get("permit_in"),
            "invert_output": self._reg.get("invert"),
        }

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        await self.coordinator.async_set_ds_regulator(self._index, setpoint=float(temperature))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_set_ds_regulator(self._index, enabled=False)
            return
        await self.coordinator.async_set_ds_regulator(
            self._index,
            enabled=True,
            mode=1 if hvac_mode == HVACMode.COOL else 0,
        )

    async def async_turn_on(self) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, enabled=True)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_set_ds_regulator(self._index, enabled=False)
