"""MongoDB billing operations for local LegalTech development."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from pymongo import MongoClient

from app.config.settings import settings


class MongoBillingService:
    """Tenant-scoped time-entry and invoice-preview operations."""

    def __init__(self):
        if not settings.MONGODB_URL:
            raise RuntimeError("MONGODB_URL is not configured.")
        self.client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        self.database = self.client[settings.MONGODB_DATABASE]
        self.entries = self.database["time_entries"]
        self.invoices = self.database["invoices"]

    def create_time_entry(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        matter_id: UUID,
        work_date,
        duration_minutes: int,
        rate: Decimal,
        description: str,
    ) -> dict:
        entry = {
            "_id": str(uuid4()),
            "organization_id": str(organization_id),
            "user_id": str(user_id),
            "matter_id": str(matter_id),
            "work_date": datetime.combine(work_date, datetime.min.time()),
            "duration_minutes": duration_minutes,
            "rate": str(rate),
            "description": description,
            "billed_status": "unbilled",
            "created_at": datetime.utcnow(),
        }
        self.entries.insert_one(entry)
        return entry

    def list_time_entries(self, *, organization_id: UUID, matter_id: UUID):
        return list(
            self.entries.find(
                {
                    "organization_id": str(organization_id),
                    "matter_id": str(matter_id),
                }
            ).sort("work_date", -1)
        )

    def preview_unbilled(
        self, *, organization_id: UUID, matter_id: UUID, tax_rate: Decimal
    ) -> dict:
        entries = list(
            self.entries.find(
                {
                    "organization_id": str(organization_id),
                    "matter_id": str(matter_id),
                    "billed_status": "unbilled",
                }
            )
        )
        subtotal = Decimal("0")
        line_items = []
        for entry in entries:
            rate = Decimal(entry["rate"])
            amount = (
                Decimal(entry["duration_minutes"]) / Decimal("60") * rate
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal += amount
            line_items.append(
                {
                    "time_entry_id": entry["_id"],
                    "description": entry["description"],
                    "work_date": entry["work_date"].date().isoformat(),
                    "duration_minutes": entry["duration_minutes"],
                    "rate": float(rate),
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

    def create_invoice(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        matter_id: UUID,
        tax_rate: Decimal,
        currency: str,
    ) -> dict:
        preview = self.preview_unbilled(
            organization_id=organization_id,
            matter_id=matter_id,
            tax_rate=tax_rate,
        )
        if not preview["line_items"]:
            raise ValueError("No unbilled time entries exist for this matter.")

        now = datetime.utcnow()
        invoice_id = str(uuid4())
        invoice = {
            "_id": invoice_id,
            "organization_id": str(organization_id),
            "created_by": str(user_id),
            "matter_id": str(matter_id),
            "currency": currency.upper(),
            "status": "issued",
            "tax_rate": str(tax_rate),
            "line_items": preview["line_items"],
            "subtotal": preview["subtotal"],
            "tax": preview["tax"],
            "total": preview["total"],
            "created_at": now,
        }
        self.invoices.insert_one(invoice)

        entry_ids = [item["time_entry_id"] for item in preview["line_items"]]
        self.entries.update_many(
            {
                "_id": {"$in": entry_ids},
                "organization_id": str(organization_id),
                "matter_id": str(matter_id),
                "billed_status": "unbilled",
            },
            {
                "$set": {
                    "billed_status": "invoiced",
                    "invoice_id": invoice_id,
                    "updated_at": now,
                }
            },
        )
        return invoice
