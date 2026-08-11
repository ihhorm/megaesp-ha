# Зміни

## 2026-08-11

### Home Assistant docs

- Оновлено документацію сумісності з прошивкою `MegaESP Firmware 11.6`.
- Додано згадку про `Wi-Fi Indicator Output` і heartbeat-індикацію Wi-Fi LED.

## 2026-08-05

### Home Assistant `2026.8.5`

- Додано окрему HACS-готову інтеграцію `MegaESP` для Home Assistant.
- Додано сутності `Permit Input` для регуляторів `DS18B20`, `Pressure`, `Differential`.
- Додано сутності `Invert output` для всіх основних типів регуляторів.
- Додано `climate` сутності для терморегуляторів `DS18B20`.
- Додано авто-генерацію панелі `MegaESP` у Home Assistant.
- Додано окремі переходи `HA` і `Web` у панелі контролера.
- Прибрано дублювання `Pressure` і `Differential` у панелі.
- Перейменовано секцію `Device Status` у `Analog Input`.
- Підготовлено репозиторій до встановлення через HACS.
