from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from .models import ChangeLog, License
from .schemas import LicenseCreate
from .settings import get_settings

TRACKED_FIELDS = [
    "product_name", "license_type", "category", "target_system", "owner_name",
    "vendor_name", "start_date", "end_date", "warning_days", "contract_number",
    "document_url", "cost", "currency", "auto_renew", "source", "comment",
]


def calculate_status(end_date: date, warning_days: int | None = None) -> str:
    settings = get_settings()
    today = date.today()
    days_left = (end_date - today).days
    if days_left < 0:
        return "expired"
    if days_left <= settings.urgent_days:
        return "urgent"
    if days_left <= settings.critical_days:
        return "critical"
    if days_left <= (warning_days if warning_days is not None else settings.warning_days):
        return "warning"
    return "active"


def stringify(value) -> str | None:
    if value is None:
        return None
    return str(value)


def add_log(db: Session, license_id: int | None, action: str, field_name: str | None = None, old_value=None, new_value=None, actor: str = "web") -> None:
    db.add(ChangeLog(
        license_id=license_id,
        action=action,
        field_name=field_name,
        old_value=stringify(old_value),
        new_value=stringify(new_value),
        actor=actor,
    ))


def refresh_all_statuses(db: Session) -> None:
    items = list(db.scalars(select(License)).all())
    changed = False
    for item in items:
        new_status = calculate_status(item.end_date, item.warning_days)
        if item.status != new_status:
            add_log(db, item.id, "status_auto_update", "status", item.status, new_status, "system")
            item.status = new_status
            changed = True
    if changed:
        db.commit()


def build_query(q: str | None = None, status: str | None = None, owner: str | None = None, category: str | None = None, source: str | None = None):
    stmt = select(License).order_by(License.end_date.asc(), License.product_name.asc())
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            License.product_name.ilike(pattern), License.target_system.ilike(pattern),
            License.owner_name.ilike(pattern), License.vendor_name.ilike(pattern),
            License.contract_number.ilike(pattern), License.comment.ilike(pattern),
        ))
    if status:
        stmt = stmt.where(License.status == status)
    if owner:
        stmt = stmt.where(License.owner_name == owner)
    if category:
        stmt = stmt.where(License.category == category)
    if source:
        stmt = stmt.where(License.source == source)
    return stmt


def get_all_licenses(db: Session, q: str | None = None, status: str | None = None, owner: str | None = None, category: str | None = None, source: str | None = None) -> list[License]:
    refresh_all_statuses(db)
    return list(db.scalars(build_query(q, status, owner, category, source)).all())


def get_license(db: Session, license_id: int) -> License | None:
    refresh_all_statuses(db)
    return db.scalar(select(License).where(License.id == license_id).options(joinedload(License.history)))


def get_filter_values(db: Session) -> dict[str, list[str]]:
    items = list(db.scalars(select(License)).all())
    return {
        "owners": sorted({x.owner_name for x in items if x.owner_name and x.owner_name != "-"}),
        "categories": sorted({x.category for x in items if x.category}),
        "sources": sorted({x.source for x in items if x.source}),
        "statuses": ["active", "warning", "critical", "urgent", "expired"],
    }


def get_expiring_licenses(db: Session, days: int) -> list[License]:
    refresh_all_statuses(db)
    today = date.today()
    stmt = select(License).where(License.end_date >= today).order_by(License.end_date.asc())
    return [item for item in db.scalars(stmt).all() if item.days_left(today) <= days]


def get_monitoring_summary(db: Session) -> dict:
    items = get_all_licenses(db)
    today = date.today()
    return {
        "total": len(items),
        "expired": sum(1 for x in items if x.days_left(today) < 0),
        "urgent": sum(1 for x in items if x.status == "urgent"),
        "critical": sum(1 for x in items if x.status == "critical"),
        "warning": sum(1 for x in items if x.status == "warning"),
        "active": sum(1 for x in items if x.status == "active"),
        "items": [
            {
                "id": x.id,
                "product_name": x.product_name,
                "target_system": x.target_system,
                "owner_name": x.owner_name,
                "category": x.category,
                "end_date": x.end_date.isoformat(),
                "days_left": x.days_left(today),
                "status": x.status,
            }
            for x in items if x.status in {"warning", "critical", "urgent", "expired"}
        ],
    }


def create_license(db: Session, payload: LicenseCreate, actor: str = "web") -> License:
    obj = License(**payload.model_dump())
    obj.status = calculate_status(obj.end_date, obj.warning_days)
    db.add(obj)
    db.flush()
    add_log(db, obj.id, "create", None, None, obj.product_name, actor)
    db.commit()
    db.refresh(obj)
    return obj


def update_license(db: Session, license_id: int, payload: LicenseCreate, actor: str = "web") -> License | None:
    obj = db.get(License, license_id)
    if obj is None:
        return None
    data = payload.model_dump()
    for key, new_value in data.items():
        old_value = getattr(obj, key)
        if stringify(old_value) != stringify(new_value):
            add_log(db, license_id, "update", key, old_value, new_value, actor)
            setattr(obj, key, new_value)
    new_status = calculate_status(obj.end_date, obj.warning_days)
    if obj.status != new_status:
        add_log(db, license_id, "status_update", "status", obj.status, new_status, actor)
        obj.status = new_status
    db.commit()
    db.refresh(obj)
    return obj


def delete_license(db: Session, license_id: int, actor: str = "web") -> bool:
    obj = db.get(License, license_id)
    if obj is None:
        return False
    add_log(db, license_id, "delete", None, obj.product_name, None, actor)
    db.delete(obj)
    db.commit()
    return True


def get_recent_history(db: Session, limit: int = 100) -> list[ChangeLog]:
    stmt = select(ChangeLog).order_by(ChangeLog.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def seed_demo_data(db: Session) -> None:
    exists = db.scalar(select(License.id).limit(1))
    if exists:
        return
    today = date.today()
    demo_items: Iterable[License] = [
        License(product_name="Zabbix Support", license_type="support", category="software", target_system="zabbix-prod-01", owner_name="Infra Team", vendor_name="Zabbix", end_date=today.replace(year=today.year + 1), warning_days=60, contract_number="SUP-2026-001", source="manual", comment="Продление через партнёра", status="active"),
        License(product_name="Vinteo MCU", license_type="subscription", category="software", target_system="vinteo-core", owner_name="Video Team", vendor_name="Vinteo", end_date=today, warning_days=45, contract_number="VIN-2026-014", source="api", comment="Нужно уточнять количество лицензий", status="urgent"),
        License(product_name="SSL wildcard *.example.local", license_type="certificate", category="ssl", target_system="nginx-gateway", owner_name="Web Team", vendor_name="Internal CA", end_date=today, warning_days=30, contract_number="CERT-INT-77", auto_renew=True, source="auto", comment="Проверить автоперевыпуск", status="urgent"),
    ]
    for item in demo_items:
        item.status = calculate_status(item.end_date, item.warning_days)
        db.add(item)
        db.flush()
        add_log(db, item.id, "create", None, None, item.product_name, "seed")
    db.commit()
