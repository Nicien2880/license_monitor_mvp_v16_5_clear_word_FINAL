from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class HardwareSupport(Base):
    __tablename__ = "hardware_support"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dzo: Mapped[str] = mapped_column(String(255), nullable=False, default="-", index=True)
    serial_number: Mapped[str] = mapped_column(String(255), nullable=False, default="-", index=True)
    equipment_model: Mapped[str] = mapped_column(String(255), nullable=False, default="-", index=True)
    delivery_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    support_end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    purchase_period: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    contractor: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    auto_renewal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def days_left(self, today: date | None = None) -> int:
        today = today or date.today()
        return (self.support_end_date - today).days


class SoftwareLicense(Base):
    __tablename__ = "software_licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(255), nullable=False, default="-", index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cert_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cert_end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    certificate_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    contractor: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def days_left(self, today: date | None = None) -> int:
        today = today or date.today()
        return (self.cert_end_date - today).days


class BackupObject(Base):
    __tablename__ = "backup_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    object_name: Mapped[str] = mapped_column(String(255), nullable=False, default="-", index=True)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False, default="vm", index=True)
    platform: Mapped[str] = mapped_column(String(120), nullable=False, default="manual", index=True)
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    next_backup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    size_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="success", index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def hours_since_backup(self, now: datetime | None = None) -> int | None:
        if self.last_backup_at is None:
            return None
        now = now or datetime.utcnow()
        return int((now - self.last_backup_at).total_seconds() // 3600)


class DataProtectionPolicy(Base):
    __tablename__ = "data_protection_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    backup_type: Mapped[str] = mapped_column(String(120), nullable=False, default="filesystem", index=True)
    system_name: Mapped[str] = mapped_column(String(255), nullable=False, default="-", index=True)
    reserved_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_volume_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    procedure_frequency: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_period: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_person: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChangeLog(Base):
    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    section: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="viewer", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
