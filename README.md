# MegaESP для Home Assistant

[![Validate](https://github.com/ihhorm/megaesp-ha/actions/workflows/validate.yaml/badge.svg)](https://github.com/ihhorm/megaesp-ha/actions/workflows/validate.yaml) [![Hassfest](https://github.com/ihhorm/megaesp-ha/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/ihhorm/megaesp-ha/actions/workflows/hassfest.yaml) [![Release](https://img.shields.io/github/v/release/ihhorm/megaesp-ha)](https://github.com/ihhorm/megaesp-ha/releases)

Кастомна інтеграція Home Assistant для контролерів MegaESP / ESP8266 MegaD.

## Можливості

- локальне опитування через HTTP API MegaESP
- керування `Output`, `PWM`, лічильниками `Input`, `Analog Input`
- сенсори `DS18B20`
- I2C сенсори
- регулятор тиску
- диференційний регулятор
- терморегулятори `DS18B20` як стандартні сутності `climate.*`
- автоматично згенерована панель `MegaESP` у Home Assistant
- сумісність із прошивкою `MegaESP Firmware 11.6` (`Wi-Fi Indicator Output`, heartbeat Wi-Fi LED)

## Встановлення через HACS

1. Відкрий `HACS` у Home Assistant.
2. Відкрий меню у правому верхньому куті.
3. Обери `Custom repositories`.
4. Додай `https://github.com/ihhorm/megaesp-ha`.
5. Вибери категорію `Integration`.
6. Встанови `MegaESP`.
7. Перезапусти Home Assistant.
8. Перейди в `Settings -> Devices & services`.
9. Додай інтеграцію `MegaESP`.

## Налаштування

Потрібні параметри:

- IP-адреса або hostname контролера
- HTTP порт контролера, зазвичай `80`
- пароль контролера з прошивки MegaESP
- інтервал опитування в секундах

## Картка Thermostat

Терморегулятори `DS18B20` експортуються як стандартні сутності Home Assistant `climate`.

1. Відкрий потрібний dashboard.
2. Обери `Edit dashboard`.
3. Додай картку `Thermostat`.
4. Вибери потрібну сутність `climate.megaesp...`.

## Брендинг Home Assistant

Інтеграція містить локальні brand assets всередині `custom_components/megaesp/brand`, тому іконка та логотип доступні без зовнішніх залежностей.

## Підтримка

- Issues: https://github.com/ihhorm/megaesp-ha/issues
- Прошивка: https://github.com/ihhorm/megaesp-firmware

## Версія

Поточний HACS release: `2026.8.5`


## Детальна інструкція встановлення

Покрокова інструкція: `INSTALL.md`
