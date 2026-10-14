"""Billing operations for the additive LegalTech time-tracking module."""

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.legaltech import TimeEntry


class BillingService:
    """Build tenant-scoped billing previews from unbilled time entries."""

    @staticmethod
    def create_time_entry(
        session: Session,
        *,
        organization_id: UUID,
        user_id: UUID,
        matter_id: UUID,
        work_date,
        duration_minutes: int,
        rate: Decimal,
        description: str,
    ) -> TimeEntry:
        entry = TimeEntry(
            organization_id=organization_id,
            user_id=user_id,
            matter_id=matter_id,
            work_date=work_date,
            duration_minutes=duration_minutes,
            rate=rate,
            description=description,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry

    @staticmethod
    def list_time_entries(session: Session, *, organization_id: UUID, matter_id: UUID):
        statement = (
            select(TimeEntry)
            .where(
                TimeEntry.organization_id == organization_id,
                TimeEntry.matter_id == matter_id,
            )
            .order_by(TimeEntry.work_date.desc(), TimeEntry.created_at.desc())
        )
        return list(session.scalars(statement))

    @staticmethod
    def preview_unbilled(
        session: Session,
        *,
        organization_id: UUID,
        matter_id: UUID,
        tax_rate: Decimal = Decimal("0"),
    ) -> dict:
        statement = select(TimeEntry).where(
            TimeEntry.organization_id == organization_id,
            TimeEntry.matter_id == matter_id,
            TimeEntry.billed_status == "unbilled",
        )
        entries = list(session.scalars(statement))
        line_items = []
        subtotal = Decimal("0")
        for entry in entries:
            amount = (
                Decimal(entry.duration_minutes) / Decimal("60") * entry.rate
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal += amount
            line_items.append(
                {
                    "time_entry_id": str(entry.id),
                    "description": entry.description,
                    "work_date": entry.work_date.isoformat(),
                    "duration_minutes": entry.duration_minutes,
                    "rate": float(entry.rate),
                    "amount": float(amount),
                }
            )
        tax = (subtotal * tax_rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return {
            "matter_id": str(matter_id),
            "currency": "INR",
            "line_items": line_items,
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total": float(subtotal + tax),
        }
