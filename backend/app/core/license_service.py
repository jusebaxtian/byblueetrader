from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.license_repository import License, LicenseRepository


@dataclass
class ValidationResult:
    valid: bool
    status: str  # "active" | "inactive" | "expired" | "not_found"
    expires_at: datetime | None


def validate_license(repo: LicenseRepository, iq_email: str) -> ValidationResult:
    license_ = repo.get_license_by_email(iq_email)
    if license_ is None:
        return ValidationResult(valid=False, status="not_found", expires_at=None)

    if license_.status != "active":
        return ValidationResult(valid=False, status="inactive", expires_at=license_.expires_at)

    if license_.expires_at is not None and license_.expires_at < datetime.now(timezone.utc):
        return ValidationResult(valid=False, status="expired", expires_at=license_.expires_at)

    repo.touch_last_seen(license_.id)
    return ValidationResult(valid=True, status="active", expires_at=license_.expires_at)
