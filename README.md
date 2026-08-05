# MegaESP для Home Assistant

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

## Підтримка

- Issues: https://github.com/ihhorm/megaesp-ha/issues
- Прошивка: https://github.com/ihhorm/megaesp-firmware

## Версія

Поточний HACS release: `2026.8.5`
