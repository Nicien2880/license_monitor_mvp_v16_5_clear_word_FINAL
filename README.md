# License Monitor v14

Внутренний веб-сервис для контроля сроков техподдержки оборудования и лицензий ПО.

## Что нового в v14

- добавлено резервное копирование SQLite-базы из UI;
- страница `/admin/backups` для создания, скачивания и удаления backup-файлов;
- backup доступен только роли `admin`;
- путь к backup-папке задаётся через `BACKUP_DIR`;
- экран входа очищен от технических подсказок.

## Что нового в v13

- добавлена авторизация через `/login` и `/logout`;
- добавлены роли `viewer`, `editor`, `manager`, `admin`;
- добавлена страница управления пользователями `/admin/users`;
- опасные операции закрыты правами на backend-уровне;
- кнопки в интерфейсе скрываются по роли пользователя;
- API для Zabbix можно закрыть через `X-API-Key`;
- первый admin создаётся автоматически из `.env` при первом запуске.

## Роли

```text
viewer   — только просмотр
editor   — просмотр + добавление + редактирование
manager  — editor + удаление + импорт/экспорт Excel
admin    — manager + управление пользователями
```

## Быстрый запуск

```bash
cd license_monitor_mvp_v13
cp .env.example .env
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

После запуска открой:

```text
http://IP_СЕРВЕРА:8000/
```

По умолчанию будет создан первый администратор из `.env`:

```env
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=ChangeMe123!
```

После первого входа пароль лучше поменять через `/admin/users`.

## Настройки авторизации в .env

```env
AUTH_ENABLED=true
SESSION_SECRET=change-this-to-long-random-string
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=ChangeMe123!
INITIAL_ADMIN_EMAIL=admin@company.local

# Если заполнено — API требует заголовок X-API-Key.
# Если пусто — API открыт внутри сети.
ZABBIX_API_KEY=change-me-zabbix-token
```

Важно: `SESSION_SECRET` лучше заменить на длинную случайную строку.

## Основные страницы

```text
/                         веб-интерфейс
/login                    вход
/logout                   выход
/admin/users              пользователи, только admin
/?section=hardware         техподдержка оборудования
/?section=software         лицензии ПО
/history                  история изменений
/export.xlsx?section=hardware
/export.xlsx?section=software
```

## API

```text
/api/licenses
/api/licenses?section=hardware
/api/licenses?section=software
/api/licenses/expiring?days=30
/api/licenses/expiring?days=30&section=hardware
/api/hardware-support
/api/software-licenses
/api/monitoring/summary
/api/zabbix/summary
/metrics
```

Если задан `ZABBIX_API_KEY`, дергай API так:

```bash
curl -H "X-API-Key: change-me-zabbix-token" \
  http://IP_СЕРВЕРА:8000/api/zabbix/summary
```

## Инструкция для Zabbix

### HTTP agent master item

Создай host, например:

```text
License Monitor
```

Добавь item:

```text
Name: License Monitor: Zabbix summary raw
Type: HTTP agent
Key: license_monitor.summary.raw
URL: http://IP_СЕРВЕРА:8000/api/zabbix/summary
Request method: GET
Type of information: Text
Update interval: 5m или 10m
```

Если включён API-ключ, добавь header:

```text
Header name: X-API-Key
Header value: change-me-zabbix-token
```

Master item возвращает JSON:

```json
{
  "hardware_total": 10,
  "hardware_warning": 2,
  "hardware_critical": 1,
  "hardware_urgent": 0,
  "hardware_expired": 0,
  "software_total": 15,
  "software_warning": 3,
  "software_critical": 1,
  "software_urgent": 1,
  "software_expired": 0,
  "total_expired": 0,
  "total_urgent": 1,
  "total_critical": 2,
  "total_warning": 5
}
```

### Dependent items

```text
Name: License Monitor: total expired
Type: Dependent item
Key: license_monitor.total.expired
Master item: License Monitor: Zabbix summary raw
Preprocessing: JSONPath -> $.total_expired
Type of information: Numeric unsigned
```

```text
Name: License Monitor: software urgent
Type: Dependent item
Key: license_monitor.software.urgent
Master item: License Monitor: Zabbix summary raw
Preprocessing: JSONPath -> $.software_urgent
Type of information: Numeric unsigned
```

```text
Name: License Monitor: hardware critical
Type: Dependent item
Key: license_monitor.hardware.critical
Master item: License Monitor: Zabbix summary raw
Preprocessing: JSONPath -> $.hardware_critical
Type of information: Numeric unsigned
```

### Примеры триггеров

```text
last(/License Monitor/license_monitor.total.expired)>0
```

```text
last(/License Monitor/license_monitor.total.urgent)>0
```

```text
last(/License Monitor/license_monitor.total.critical)>0
```

Severity можно разложить так:

```text
Expired > 0   -> High
Urgent > 0    -> Average
Critical > 0  -> Warning
```

## Перед обновлением рабочей версии

Сделай бэкап папки проекта и базы:

```bash
cp -r /opt/license_monitor /opt/license_monitor_backup_$(date +%F)
```

Если база уже рабочая, не удаляй папку `data/` без резервной копии.


## Резервные копии базы из UI

Страница доступна только администратору:

```text
/admin/backups
```

Что можно сделать:

```text
Создать резервную копию
Скачать резервную копию
Удалить старую резервную копию
```

По умолчанию копии складываются в:

```env
BACKUP_DIR=./data/backups
```

При Docker-запуске папка `./data` смонтирована как volume, поэтому backup-файлы остаются на хосте.

Восстановление intentionally не сделано кнопкой в UI, чтобы случайно не перезаписать рабочую базу. Для ручного восстановления останови сервис и замени файл базы на нужную копию:

```bash
sudo systemctl stop license-monitor
cp ./data/backups/license_monitor_backup_YYYYMMDD_HHMMSS_admin.db ./data/licenses.db
sudo systemctl start license-monitor
```

---

## Запуск через Nginx + systemd

Для продового/полупродового запуска используйте файлы из папки `deploy/`:

- `deploy/license-monitor.service` — systemd unit;
- `deploy/nginx-license-monitor.conf` — reverse proxy для Nginx.

Подробная инструкция для RED OS 8 лежит в файле:

```text
README_NGINX_REDSOS.md
```

Итоговая схема:

```text
Browser -> Nginx :80 -> FastAPI/Uvicorn 127.0.0.1:8000 -> SQLite
```

## v15: Backup monitoring dashboard

Добавлен раздел `/backup-monitor` для визуального контроля резервных копий серверов и виртуальных машин.

Подробности: `README_BACKUP_MONITORING.md`.

## v16: Data Protection — политики резервирования

Добавлен новый раздел `/data-protection` для визуализации таблицы из регламента резервного копирования информационных систем.

### Что появилось

- отдельный пункт меню **Data Protection**;
- dashboard по плану резервирования ИС;
- группировка строк по типам backup:
  - `Filesystem`;
  - `Internal Database`;
  - `MS SQL Server`;
  - `Virtual Environment`;
- карточка политики по клику на строку;
- редактирование политики из карточки;
- удаление политики из карточки/таблицы;
- импорт и экспорт Excel;
- API:
  - `GET /api/data-protection/plan`;
  - `GET /api/data-protection/summary`.

### Колонки раздела Data Protection

- №;
- Тип backup;
- Наименование информационной системы;
- Информация, подлежащая резервированию;
- Максимальный объём, ГБ;
- Периодичность проведения процедуры;
- Срок хранения информации;
- Примечания;
- Ответственный работник.

### Формат Excel для импорта

Первая строка — заголовки. Порядок колонок:

```text
№ | Тип backup | Наименование информационной системы | Информация, подлежащая резервированию | Максимальный объём, ГБ | Периодичность проведения процедуры | Срок хранения информации | Примечания | Ответственный работник
```

Значения для `Тип backup` можно писать как:

```text
filesystem
internal_database
ms_sql_server
virtual_environment
```

или человекочитаемо:

```text
Filesystem
Internal Database
MS SQL Server
Virtual Environment
```

### API для проверки

```bash
curl -H "X-API-Key: $ZABBIX_API_KEY" \
  http://127.0.0.1:8000/api/data-protection/summary
```

Через nginx:

```bash
curl -H "X-API-Key: $ZABBIX_API_KEY" \
  http://127.0.0.1/api/data-protection/summary
```
