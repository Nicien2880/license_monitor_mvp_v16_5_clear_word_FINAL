from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LicenseBase(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=255)
    license_type: str = "subscription"
    category: str = "software"
    target_system: str = "-"
    owner_name: str = "-"
    vendor_name: str = "-"
    start_date: date | None = None
    end_date: date
    warning_days: int = 60
    contract_number: str | None = None
    document_url: str | None = None
    cost: Decimal | None = None
    currency: str | None = "RUB"
    auto_renew: bool = False
    source: str = "manual"
    comment: str | None = None


class LicenseCreate(LicenseBase):
    pass


class LicenseRead(LicenseBase):
    id: int
    status: str
    days_left: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChangeLogRead(BaseModel):
    id: int
    license_id: int | None = None
    action: str
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    actor: str
    created_at: datetime

    model_config = {"from_attributes": True}
