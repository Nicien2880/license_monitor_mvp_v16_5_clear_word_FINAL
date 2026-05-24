# License Monitor v15 — раздел «Резервные копии объектов»

В v15 добавлен новый ресурс веб-интерфейса:

```text
/backup-monitor
```

Он предназначен для визуального контроля резервных копий серверов, виртуальных машин, баз данных и сервисов.

## Что добавлено

- левое меню: пункт **Резервные копии объектов**;
- dashboard с KPI:
  - всего объектов;
  - успешно;
  - требуют проверки;
  - ошибки;
  - выполняется сейчас;
- визуализация статусов;
- группировка по платформам: VMware, Proxmox, Windows Server, Linux, Veeam и т.д.;
- таблица объектов backup-мониторинга;
- карточка объекта по клику;
- редактирование из карточки;
- удаление из карточки и таблицы;
- сортировка и изменение ширины столбцов;
- API для интеграций.

## Поля объекта резервного копирования

```text
Объект
Тип объекта
Платформа
Последний backup
Следующий backup
Размер, ГБ
Хранилище
Retention, дней
Длительность, мин
Политика / задание
Ответственный
Статус
Комментарий
```

## Статусы

```text
success  — backup успешен
warning  — требует проверки
failed   — ошибка
running  — выполняется сейчас
unknown  — неизвестно / данных нет
```

## API

Все API защищены тем же ключом `X-API-Key`, что и остальные endpoint'ы.

Список объектов:

```bash
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:8000/api/backup-monitor
```

Сводка:

```bash
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:8000/api/backup-monitor/summary
```

Через Nginx:

```bash
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1/api/backup-monitor/summary
```

## Zabbix

Можно сделать HTTP agent item:

```text
URL: http://IP_СЕРВЕРА/api/backup-monitor/summary
Headers:
X-API-Key: YOUR_KEY
```

Полезные JSONPath:

```text
$.stats.total
$.stats.success
$.stats.warning
$.stats.failed
$.stats.running
$.stats.health
```

Триггер на ошибки:

```text
last(/License Monitor/backup.failed)>0
```

Триггер на снижение успешности:

```text
last(/License Monitor/backup.health)<95
```

## Обновление поверх v14

Не удаляй `data/` и `.env`.

Пример безопасного обновления:

```bash
sudo systemctl stop license-monitor
cp -a /opt/license-monitor /opt/license-monitor_before_v15
rsync -av --exclude 'data/' --exclude '.env' ./license_monitor_mvp_v15_backup_dashboard/ /opt/license-monitor/
sudo chown -R license-monitor:license-monitor /opt/license-monitor
sudo systemctl start license-monitor
```

При первом запуске SQLAlchemy создаст новую таблицу `backup_objects`. Существующие таблицы и данные не удаляются.
