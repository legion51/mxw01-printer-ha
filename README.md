# MXW01 Bluetooth Printer для Home Assistant

Репозиторий содержит два компонента:

- `mxw01_printer` — Home Assistant add-on, который получает задания, рендерит их в 384-точечный монохромный растр и передаёт по Bluetooth протоколу MXW01 (AE01/AE03);
- `custom_components/mxw01_printer` — custom integration, добавляющая действие `mxw01_printer.print` для автоматизаций и панели Developer Tools.

## Установка

1. Создайте GitHub-репозиторий и загрузите в него содержимое этой папки. Перед публикацией замените URL `your-github-user` в `repository.yaml`, `config.yaml` и `manifest.json`.
2. В Home Assistant OS откройте **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, добавьте URL репозитория и установите **MXW01 Bluetooth Printer**.
3. В настройках add-on укажите Bluetooth-адрес принтера. Его можно узнать в логах Home Assistant/BlueZ или оставить пустым: мост выполнит сканирование по имени `MXW01` перед первой печатью.
4. Запустите add-on. Home Assistant должен иметь доступ к Bluetooth-адаптеру, а принтер быть включён и не занят приложением телефона.
5. Скопируйте каталог `custom_components/mxw01_printer` в `/config/custom_components/mxw01_printer/`, перезапустите Home Assistant и добавьте интеграцию **MXW01 Bluetooth Printer** в **Settings → Devices & services**. Оставьте адрес моста по умолчанию: `http://mxw01_printer:8099`.

Add-on рассчитан на Home Assistant OS/Supervised. Обычный Home Assistant Container не предоставляет Supervisor, поэтому add-on там не устанавливается; мост следует запускать отдельным контейнером с доступом к системному D-Bus/BlueZ.

## Пример автоматизации

```yaml
alias: Напечатать уведомление
triggers:
  - trigger: state
    entity_id: binary_sensor.door
    to: "on"
actions:
  - action: mxw01_printer.print
    data:
      markdown: |
        # Открыта дверь
        [C]{{ now().strftime('%d.%m.%Y %H:%M') }}
        ---
        [QR:https://my.home-assistant.io|4]
      font_size: 20
      qr_size: 4
mode: single
```

## Поддерживаемая разметка

| Синтаксис | Результат |
| --- | --- |
| `# Заголовок` | увеличенный шрифт |
| `[C] Текст` | центрированный текст |
| `[QR:данные|4]` | QR-код, размер модуля 1–10 |
| `[IMG:https://example.org/a.png|80]` | удалённая картинка, масштаб 20–200% |
| `---`, `===` | тонкая / двойная линия |

Картинки загружаются только по HTTP(S) и ограничены 10 МБ. Это намеренное ограничение: add-on не получает доступ к произвольным файлам Home Assistant.

## Проверка связи

После запуска ingress-страница add-on показывает JSON со статусом. Для диагностики можно открыть `GET /scan` через ingress — ответ содержит найденные устройства с именем, включающим `MXW01`.

## Лицензия

Добавьте выбранную вами лицензию перед публикацией. BLE-пакетирование и форматирование построены на основе предоставленного исходного приложения MXW01.
