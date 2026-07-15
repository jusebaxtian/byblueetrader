import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.license_service import validate_license
from app.repositories.license_repository import License, LicenseRepository


class FakeRepo(LicenseRepository):
    def __init__(self, licenses: dict[str, License]):
        self._licenses = licenses
        self.touched: list[str] = []

    def get_license_by_email(self, iq_email):
        return self._licenses.get(iq_email)

    def touch_last_seen(self, license_id):
        self.touched.append(license_id)

    def list_users(self):
        return list(self._licenses.values())

    def create_user_with_license(self, iq_email, plan, expires_at):
        raise NotImplementedError

    def update_license(self, license_id, status=None, expires_at=None, plan=None):
        raise NotImplementedError


def make_license(status, expires_at) -> License:
    return License(id="lic-1", user_id="user-1", iq_email="trader@example.com", status=status, expires_at=expires_at)


def test_valid_active_not_expired():
    future = datetime.now(timezone.utc) + timedelta(days=10)
    repo = FakeRepo({"trader@example.com": make_license("active", future)})
    result = validate_license(repo, "trader@example.com")
    assert result.valid is True
    assert result.status == "active"
    assert repo.touched == ["lic-1"]


def test_expired_license_is_invalid():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    repo = FakeRepo({"trader@example.com": make_license("active", past)})
    result = validate_license(repo, "trader@example.com")
    assert result.valid is False
    assert result.status == "expired"


def test_inactive_license_is_invalid():
    future = datetime.now(timezone.utc) + timedelta(days=10)
    repo = FakeRepo({"trader@example.com": make_license("inactive", future)})
    result = validate_license(repo, "trader@example.com")
    assert result.valid is False
    assert result.status == "inactive"


def test_unknown_email_not_found():
    repo = FakeRepo({})
    result = validate_license(repo, "ghost@example.com")
    assert result.valid is False
    assert result.status == "not_found"


def test_license_without_expiration_is_valid_indefinitely():
    repo = FakeRepo({"trader@example.com": make_license("active", None)})
    result = validate_license(repo, "trader@example.com")
    assert result.valid is True


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
