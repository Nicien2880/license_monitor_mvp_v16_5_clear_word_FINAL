"""
Email-уведомления для License Monitor.

Запускать cron/systemd timer раз в день.
Скрипт берёт проблемные лицензии из /api/monitoring/summary и отправляет письмо через SMTP.

Минимальные переменные окружения:
  LICENSE_MONITOR_URL=http://127.0.0.1:8000
  SMTP_HOST=smtp.company.local
  SMTP_PORT=587
  SMTP_FROM=license-monitor@company.local
  SMTP_TO=admin@company.local,it@company.local

Если SMTP требует авторизацию:
  SMTP_USER=license-monitor@company.local
  SMTP_PASSWORD=secret

Шифрование:
  SMTP_STARTTLS=true   # обычно для 587 порта
  SMTP_SSL=false       # обычно для 465 порта
"""
import json
import os
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from html import escape

BASE_URL = os.getenv("LICENSE_MONITOR_URL", "http://127.0.0.1:8000").rstrip("/")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "license-monitor@localhost")
SMTP_TO = [x.strip() for x in os.getenv("SMTP_TO", "").split(",") if x.strip()]
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "true").lower() in {"1", "true", "yes", "on"}
SMTP_SSL = os.getenv("SMTP_SSL", "false").lower() in {"1", "true", "yes", "on"}
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "20"))

STATUS_RU = {
    "warning": "Предупреждение",
    "critical": "Критично",
    "urgent": "Срочно",
    "expired": "Просрочено",
}


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def build_plain_text(items):
    lines = [
        "License Monitor: есть лицензии с риском",
        "",
        f"Источник: {BASE_URL}",
        "",
    ]
    for item in items[:50]:
        status = STATUS_RU.get(item.get("status"), item.get("status", "unknown"))
        days_left = item.get("days_left")
        days_text = "просрочено" if isinstance(days_left, int) and days_left < 0 else f"осталось {days_left} дн."
        lines.append(
            f"{status}: {item.get('product_name')} / {item.get('target_system')} — "
            f"{days_text}, дата окончания: {item.get('end_date')}"
        )
    if len(items) > 50:
        lines.append(f"...и ещё {len(items) - 50} записей")
    return "\n".join(lines)


def build_html(items):
    rows = []
    for item in items[:50]:
        status = STATUS_RU.get(item.get("status"), item.get("status", "unknown"))
        rows.append(
            "<tr>"
            f"<td>{escape(str(status))}</td>"
            f"<td>{escape(str(item.get('product_name', '')))}</td>"
            f"<td>{escape(str(item.get('target_system', '')))}</td>"
            f"<td>{escape(str(item.get('end_date', '')))}</td>"
            f"<td>{escape(str(item.get('days_left', '')))}</td>"
            "</tr>"
        )
    extra = ""
    if len(items) > 50:
        extra = f"<p>И ещё {len(items) - 50} записей.</p>"
    return f"""
    <html>
      <body>
        <h2>License Monitor: есть лицензии с риском</h2>
        <p>Источник: <a href=\"{escape(BASE_URL)}\">{escape(BASE_URL)}</a></p>
        <table border=\"1\" cellpadding=\"6\" cellspacing=\"0\">
          <thead>
            <tr>
              <th>Статус</th>
              <th>Продукт</th>
              <th>Объект</th>
              <th>Дата окончания</th>
              <th>Осталось дней</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
        {extra}
      </body>
    </html>
    """


def send_email(subject: str, text: str, html: str):
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST is required")
    if not SMTP_TO:
        raise RuntimeError("SMTP_TO is required")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = ", ".join(SMTP_TO)
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    if SMTP_SSL:
        server_ctx = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
    else:
        server_ctx = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)

    with server_ctx as server:
        server.ehlo()
        if SMTP_STARTTLS and not SMTP_SSL:
            server.starttls()
            server.ehlo()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)


def main():
    summary = get_json(f"{BASE_URL}/api/monitoring/summary")
    problem_items = summary.get("items", [])
    if not problem_items:
        print("No expiring licenses")
        return 0

    subject = f"License Monitor: проблемных лицензий — {len(problem_items)}"
    text = build_plain_text(problem_items)
    html = build_html(problem_items)
    send_email(subject, text, html)
    print("Email notification sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
