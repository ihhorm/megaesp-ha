DOMAIN = "megaesp"
DASHBOARD_CONFIG_FILENAME = "megaesp-dashboard-config.json"
DASHBOARD_FILENAME = "megaesp-dashboard.yaml"

DEFAULT_DASHBOARD_CONFIG = {
    "hidden_entities": [],
    "hidden_original_names": [],
    "rename_entities": {},
    "rename_original_names": {},
    "hidden_sections": [],
    "section_titles": {
        "controls": "Controls",
        "regulators": "Regulators",
        "inputs": "Inputs",
        "sensors": "Sensors",
        "service": "Service",
        "other_sensors": "Other Sensors",
        "device_status": "Analog Input",
    },
}

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 10

PLATFORMS = ["binary_sensor", "button", "climate", "number", "select", "sensor", "switch"]

PORT_MODE_INPUT = "input"
PORT_MODE_OUTPUT = "output"
PORT_MODE_PWM = "pwm"
PORT_MODE_ANALOG = "analog"

ONEWIRE_PORT = 3

I2C_SENSORS = [
    {
        "port": 10,
        "key": "bme280",
        "label": "BME280",
        "metrics": [
            {"field": "bme_t", "id": "temperature", "device_class": "temperature", "unit": "°C"},
            {"field": "bme_h", "id": "humidity", "device_class": "humidity", "unit": "%"},
            {"field": "bme_p", "id": "pressure", "device_class": "pressure", "unit": "hPa"},
        ],
    },
    {
        "port": 11,
        "key": "bmp180",
        "label": "BMP180",
        "metrics": [
            {"field": "bmp_t", "id": "temperature", "device_class": "temperature", "unit": "°C"},
            {"field": "bmp_p", "id": "pressure", "device_class": "pressure", "unit": "hPa"},
        ],
    },
    {
        "port": 12,
        "key": "bh1750",
        "label": "BH1750",
        "metrics": [
            {"field": "bh", "id": "illuminance", "device_class": "illuminance", "unit": "lx"},
        ],
    },
    {
        "port": 13,
        "key": "sht31",
        "label": "SHT31",
        "metrics": [
            {"field": "sht_t", "id": "temperature", "device_class": "temperature", "unit": "°C"},
            {"field": "sht_h", "id": "humidity", "device_class": "humidity", "unit": "%"},
        ],
    },
    {
        "port": 14,
        "key": "sht21",
        "label": "SHT21",
        "metrics": [
            {"field": "sht21_t", "id": "temperature", "device_class": "temperature", "unit": "°C"},
            {"field": "sht21_h", "id": "humidity", "device_class": "humidity", "unit": "%"},
        ],
    },
    {
        "port": 15,
        "key": "ina219",
        "label": "INA219",
        "metrics": [
            {"field": "ina_v", "id": "voltage", "device_class": "voltage", "unit": "V"},
            {"field": "ina_i", "id": "current", "device_class": "current", "unit": "mA"},
        ],
    },
    {
        "port": 16,
        "key": "rtc",
        "label": "RTC",
        "metrics": [
            {"field": "rtc", "id": "time", "device_class": None, "unit": None},
        ],
    },
    {
        "port": 17,
        "key": "cjmc8128",
        "label": "CJMCU-8128",
        "metrics": [
            {"field": "cjmc_co2", "id": "co2", "device_class": "carbon_dioxide", "unit": "ppm"},
            {"field": "cjmc_tvoc", "id": "tvoc", "device_class": "volatile_organic_compounds_parts", "unit": "ppb"},
            {"field": "cjmc_temp", "id": "temperature", "device_class": "temperature", "unit": "°C"},
            {"field": "cjmc_hum", "id": "humidity", "device_class": "humidity", "unit": "%"},
        ],
    },
    {
        "port": 18,
        "key": "aht20",
        "label": "AHT20",
        "metrics": [
            {"field": "aht_t", "id": "temperature", "device_class": "temperature", "unit": "°C"},
            {"field": "aht_h", "id": "humidity", "device_class": "humidity", "unit": "%"},
        ],
    },
    {
        "port": 19,
        "key": "lcd",
        "label": "PCF8574 LCD",
        "metrics": [
            {"field": "lcd_line1", "id": "line1", "device_class": None, "unit": None},
            {"field": "lcd_line2", "id": "line2", "device_class": None, "unit": None},
        ],
    },
    {
        "port": 20,
        "key": "ws281x",
        "label": "WS281x",
        "metrics": [
            {"field": "ws_r", "id": "red", "device_class": None, "unit": None},
            {"field": "ws_g", "id": "green", "device_class": None, "unit": None},
            {"field": "ws_b", "id": "blue", "device_class": None, "unit": None},
        ],
    },
]
