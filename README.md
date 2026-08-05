# MegaESP for Home Assistant

Home Assistant custom integration for MegaESP / ESP8266 MegaD controllers.

## Features

- Local polling over the MegaESP HTTP API
- Outputs, PWM, input counters, analog input
- DS18B20 sensors
- I2C sensors
- Pressure regulator
- Differential regulator
- DS18B20 thermostat entities exposed as `climate.*`
- Auto-generated MegaESP dashboard inside Home Assistant

## Installation via HACS

1. Open HACS in Home Assistant.
2. Open the top-right menu.
3. Select `Custom repositories`.
4. Add `https://github.com/ihhorm/megaesp-ha`.
5. Select category `Integration`.
6. Install `MegaESP`.
7. Restart Home Assistant.
8. Go to `Settings -> Devices & services`.
9. Add integration `MegaESP`.

## Configuration

You will need:

- controller IP address or hostname
- controller HTTP port, usually `80`
- controller password used by the MegaESP firmware
- polling interval in seconds

## Thermostat card

DS18B20 regulators are exposed as standard Home Assistant `climate` entities.

1. Open any dashboard.
2. Select `Edit dashboard`.
3. Add card `Thermostat`.
4. Choose the needed `climate.megaesp...` entity.

## Support

- Issues: https://github.com/ihhorm/megaesp-ha/issues
- Firmware: https://github.com/ihhorm/megaesp-firmware

## Version

Current HACS release target: `2026.8.5`
