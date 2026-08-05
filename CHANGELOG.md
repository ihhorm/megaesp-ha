# Changelog

## 2026-08-05

### Firmware 11.4
- Added `Permit Input` as a regulator condition/block input for DS18B20, I2C climate, Pressure, and Differential regulators.
- Added `Invert output` support for all regulator types.
- Added regulator UI controls for `Permit Input` and `Invert` on the controller web pages.

### Home Assistant
- Added `Permit Input` as HA select entities for DS, Pressure, and Differential regulators.
- Added `Invert` as HA switch entities for DS, Pressure, and Differential regulators.
- Fixed duplicated regulator cards on the MegaESP dashboard.
- Renamed dashboard section `Device Status` to `Analog Input`.
