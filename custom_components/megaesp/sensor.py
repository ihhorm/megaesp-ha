from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import I2C_SENSORS, PORT_MODE_ANALOG, PORT_MODE_INPUT
from .entity import MegaEspEntity

DEVICE_CLASS_MAP = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "pressure": SensorDeviceClass.PRESSURE,
    "illuminance": SensorDeviceClass.ILLUMINANCE,
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "carbon_dioxide": SensorDeviceClass.CO2,
    "volatile_organic_compounds_parts": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
}


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known_keys: set[str] = set()

    def build_entities() -> list[SensorEntity]:
        entities: list[SensorEntity] = []

        for port in coordinator.data["ports"].values():
            if port["hidden"]:
                continue
            if port["mode"] == PORT_MODE_ANALOG:
                key = f"analog_{port['idx']}"
                if key not in known_keys:
                    known_keys.add(key)
                    entities.append(MegaEspAnalogSensor(coordinator, entry, port["idx"]))
            if port["mode"] == PORT_MODE_INPUT:
                key = f"counter_{port['idx']}"
                if key not in known_keys:
                    known_keys.add(key)
                    entities.append(MegaEspCounterSensor(coordinator, entry, port["idx"]))

        for sensor_name in coordinator.data["onewire"]:
            key = f"onewire_{sensor_name}"
            if key in known_keys:
                continue
            known_keys.add(key)
            entities.append(MegaEspOneWireSensor(coordinator, entry, sensor_name))

        for sensor in I2C_SENSORS:
            key = sensor["key"]
            if key not in coordinator.data["i2c"]:
                continue
            for metric in sensor["metrics"]:
                metric_key = f"i2c_{key}_{metric['id']}"
                if metric_key in known_keys:
                    continue
                known_keys.add(metric_key)
                entities.append(MegaEspI2CSensor(coordinator, entry, key, metric))

        if "pressure_value" not in known_keys:
            known_keys.add("pressure_value")
            entities.append(MegaEspPressureValueSensor(coordinator, entry))

        diff_metrics = (
            ("diff_hot_temp", "hot_temp", "Differential Hot Temperature", "°C", SensorDeviceClass.TEMPERATURE),
            ("diff_tank_temp", "tank_temp", "Differential Tank Temperature", "°C", SensorDeviceClass.TEMPERATURE),
            ("diff_dt", "dt", "Differential Delta", "°C", SensorDeviceClass.TEMPERATURE),
        )
        for key, field, name, unit, device_class in diff_metrics:
            if key in known_keys:
                continue
            known_keys.add(key)
            entities.append(
                MegaEspDiffSensor(coordinator, entry, key, field, name, unit, device_class)
            )

        return entities

    entities = build_entities()
    if entities:
        async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(lambda: async_add_entities(build_entities())))


class MegaEspAnalogSensor(MegaEspEntity, SensorEntity):
    def __init__(self, coordinator, entry, port_idx: int) -> None:
        super().__init__(coordinator, entry, f"analog_p{port_idx}")
        self._port_idx = port_idx
        self._attr_name = f"{coordinator.data['ports'][port_idx]['label']} Analog"
        self._attr_native_unit_of_measurement = "ADC"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["ports"][self._port_idx]["numeric_value"]


class MegaEspCounterSensor(MegaEspEntity, SensorEntity):
    def __init__(self, coordinator, entry, port_idx: int) -> None:
        super().__init__(coordinator, entry, f"counter_p{port_idx}")
        self._port_idx = port_idx
        self._attr_name = f"{coordinator.data['ports'][port_idx]['label']} Counter"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data["ports"][self._port_idx]["counter"]


class MegaEspOneWireSensor(MegaEspEntity, SensorEntity):
    def __init__(self, coordinator, entry, sensor_name: str) -> None:
        slug = sensor_name.strip().lower().replace(" ", "_")
        super().__init__(coordinator, entry, f"onewire_{slug}")
        self._sensor_name = sensor_name
        self._attr_name = sensor_name
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = "°C"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["onewire"].get(self._sensor_name)


class MegaEspI2CSensor(MegaEspEntity, SensorEntity):
    def __init__(self, coordinator, entry, sensor_key: str, metric: dict) -> None:
        super().__init__(coordinator, entry, f"i2c_{sensor_key}_{metric['id']}")
        self._sensor_key = sensor_key
        self._metric_id = metric["id"]
        sensor_data = next(item for item in I2C_SENSORS if item["key"] == sensor_key)
        self._attr_name = f"{sensor_data['label']} {metric['id']}"
        self._attr_native_unit_of_measurement = metric["unit"]
        self._attr_device_class = DEVICE_CLASS_MAP.get(metric["device_class"])
        if metric["device_class"] in DEVICE_CLASS_MAP:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data["i2c"][self._sensor_key]["metrics"][self._metric_id]


class MegaEspPressureValueSensor(MegaEspEntity, SensorEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pressure_value")
        self._attr_name = "Pressure"
        self._attr_native_unit_of_measurement = "bar"
        self._attr_device_class = SensorDeviceClass.PRESSURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data["pressure_regulator"].get("value")


class MegaEspDiffSensor(MegaEspEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        entry,
        unique_key: str,
        field: str,
        name: str,
        unit: str,
        device_class: SensorDeviceClass,
    ) -> None:
        super().__init__(coordinator, entry, unique_key)
        self._field = field
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data["diff_regulator"].get(self._field)
