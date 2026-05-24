# License Monitor: запуск через Nginx + systemd на RED OS 8

Итоговая схема:

```text
Браузер -> Nginx :80 -> Uvicorn/FastAPI 127.0.0.1:8000 -> SQLite
```

Наружу публикуется только Nginx. FastAPI слушает только локальный адрес `127.0.0.1:8000`.

## 1. Установка зависимостей

```bash
sudo dnf install -y python3 python3-pip nginx unzip
```

Из корня проекта:

```bash
pip3 install -r requirements.txt
```

Если ставите системно и есть ограничения прав, используйте вариант, принятый в вашей среде.

## 2. Подготовка каталога

Рекомендуемый путь:

```bash
/opt/license-monitor
```

Если обновляете старую версию, не удаляйте `data/` и `.env`.

```bash
sudo mkdir -p /opt/license-monitor
sudo rsync -av --exclude 'data/' --exclude '.env' ./ /opt/license-monitor/
```

Если это первая установка:

```bash
sudo cp -a . /opt/license-monitor/
sudo cp /opt/license-monitor/.env.example /opt/license-monitor/.env
```

## 3. Системный пользователь

В RED OS путь к `nologin` обычно `/sbin/nologin`:

```bash
sudo useradd -r -s /sbin/nologin license-monitor
```

Если пользователь уже существует — это нормально.

Права:

```bash
sudo mkdir -p /opt/license-monitor/data/backups
sudo chown -R license-monitor:license-monitor /opt/license-monitor
```

## 4. Настройка .env

Откройте:

```bash
sudo nano /opt/license-monitor/.env
```

Минимально:

```env
DATABASE_URL=sqlite:///./data/licenses.db
BACKUP_DIR=./data/backups
AUTH_ENABLED=true
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=ChangeMe123!
SESSION_SECRET=change-this-long-random-secret
ZABBIX_API_KEY=change-me-zabbix-token
LICENSE_MONITOR_URL=http://IP_СЕРВЕРА
```

После первого входа желательно сменить пароль администратора через UI или заменить его в базе/механизме управления пользователями, если такая функция уже используется.

## 5. systemd-сервис

Скопируйте unit-файл:

```bash
sudo cp /opt/license-monitor/deploy/license-monitor.service /etc/systemd/system/license-monitor.service
```

Проверьте, что в нём указано:

```ini
WorkingDirectory=/opt/license-monitor
EnvironmentFile=/opt/license-monitor/.env
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
User=license-monitor
Group=license-monitor
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable license-monitor
sudo systemctl start license-monitor
sudo systemctl status license-monitor
```

Проверка локально:

```bash
curl http://127.0.0.1:8000/health
ss -lntp | grep 8000
```

Должно слушать `127.0.0.1:8000`, не `0.0.0.0:8000`.

## 6. Nginx

Скопируйте конфиг:

```bash
sudo cp /opt/license-monitor/deploy/nginx-license-monitor.conf /etc/nginx/conf.d/license-monitor.conf
```

Проверка:

```bash
sudo nginx -t
```

Запуск:

```bash
sudo systemctl enable nginx
sudo systemctl restart nginx
```

Проверка через Nginx:

```bash
curl http://127.0.0.1/health
```

С другого ПК:

```text
http://IP_СЕРВЕРА/
```

## 7. Firewall

Если firewalld включён:

```bash
sudo firewall-cmd --add-service=http --permanent
sudo firewall-cmd --reload
```

Если firewalld выключен и политика сети разрешает доступ, этот шаг не нужен.

## 8. Проверка API для Zabbix

Через приложение напрямую:

```bash
curl -H "X-API-Key: change-me-zabbix-token" http://127.0.0.1:8000/api/zabbix/summary
```

Через Nginx:

```bash
curl -H "X-API-Key: change-me-zabbix-token" http://127.0.0.1/api/zabbix/summary
```

В Zabbix лучше указывать URL через Nginx:

```text
http://IP_СЕРВЕРА/api/zabbix/summary
```

Header:

```text
X-API-Key: change-me-zabbix-token
```

## 9. Резервные копии

В UI: `Администрирование -> Резервные копии`.

Папка:

```bash
/opt/license-monitor/data/backups
```

Если ошибка 500:

```bash
grep BACKUP /opt/license-monitor/.env
grep backup_dir -n /opt/license-monitor/app/settings.py
ls -lah /opt/license-monitor/data
journalctl -u license-monitor -n 80 --no-pager
```

## 10. Обновление без удаления базы

Остановить:

```bash
sudo systemctl stop license-monitor
```

Бэкап:

```bash
sudo cp -a /opt/license-monitor /opt/license-monitor_backup_$(date +%F_%H%M)
```

Копировать новую версию без `data/` и `.env`:

```bash
sudo rsync -av --exclude 'data/' --exclude '.env' ./ /opt/license-monitor/
sudo chown -R license-monitor:license-monitor /opt/license-monitor
```

Запустить:

```bash
sudo systemctl start license-monitor
sudo systemctl status license-monitor
```
