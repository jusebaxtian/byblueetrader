"""Data access for users/licenses.

Defined as a small interface (LicenseRepository) with a Supabase-backed
implementation, so business logic (license status evaluation) can be
unit-tested against an in-memory fake without real Supabase credentials.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class License:
    id: str
    user_id: str
    iq_email: str
    status: str  # "active" | "inactive"
    expires_at: datetime | None
    plan: str | None = None
    device_id: str | None = None


class LicenseRepository(ABC):
    @abstractmethod
    def get_license_by_email(self, iq_email: str) -> License | None: ...

    @abstractmethod
    def touch_last_seen(self, license_id: str) -> None: ...

    @abstractmethod
    def list_users(self) -> list[License]: ...

    @abstractmethod
    def create_user_with_license(self, iq_email: str, plan: str, expires_at: datetime | None) -> License: ...

    @abstractmethod
    def update_license(
        self,
        license_id: str,
        status: str | None = None,
        expires_at: datetime | None = None,
        plan: str | None = None,
    ) -> License: ...


class SupabaseLicenseRepository(LicenseRepository):
    def __init__(self, client) -> None:
        self._client = client

    def get_license_by_email(self, iq_email: str) -> License | None:
        user_res = self._client.table("users").select("id, iq_email").eq("iq_email", iq_email).execute()
        if not user_res.data:
            return None
        user = user_res.data[0]

        lic_res = (
            self._client.table("licenses")
            .select("*")
            .eq("user_id", user["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not lic_res.data:
            return None
        lic = lic_res.data[0]
        return _row_to_license(lic, user["iq_email"])

    def touch_last_seen(self, license_id: str) -> None:
        self._client.table("licenses").update(
            {"last_seen_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", license_id).execute()

    def list_users(self) -> list[License]:
        res = (
            self._client.table("licenses")
            .select("*, users(iq_email)")
            .order("created_at", desc=True)
            .execute()
        )
        return [_row_to_license(row, row["users"]["iq_email"]) for row in res.data]

    def create_user_with_license(self, iq_email: str, plan: str, expires_at: datetime | None) -> License:
        user_res = self._client.table("users").upsert({"iq_email": iq_email}, on_conflict="iq_email").execute()
        user_id = user_res.data[0]["id"] if user_res.data else self._get_user_id(iq_email)

        payload = {
            "user_id": user_id,
            "status": "active",
            "plan": plan,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }
        lic_res = self._client.table("licenses").insert(payload).execute()
        lic = lic_res.data[0]
        return _row_to_license(lic, iq_email)

    def _get_user_id(self, iq_email: str) -> str:
        res = self._client.table("users").select("id").eq("iq_email", iq_email).execute()
        return res.data[0]["id"]

    def update_license(
        self,
        license_id: str,
        status: str | None = None,
        expires_at: datetime | None = None,
        plan: str | None = None,
    ) -> License:
        payload = {}
        if status is not None:
            payload["status"] = status
        if expires_at is not None:
            payload["expires_at"] = expires_at.isoformat()
        if plan is not None:
            payload["plan"] = plan

        res = self._client.table("licenses").update(payload).eq("id", license_id).execute()
        lic = res.data[0]
        user_res = self._client.table("users").select("iq_email").eq("id", lic["user_id"]).execute()
        return _row_to_license(lic, user_res.data[0]["iq_email"])


def _row_to_license(row: dict, iq_email: str) -> License:
    expires_at = row.get("expires_at")
    return License(
        id=row["id"],
        user_id=row["user_id"],
        iq_email=iq_email,
        status=row["status"],
        expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
        plan=row.get("plan"),
        device_id=row.get("device_id"),
    )
