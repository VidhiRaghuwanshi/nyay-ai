"""MongoDB-backed implementations for the remaining Nyay AI modules."""

import base64
import hashlib
import io
import re
from datetime import datetime, timezone
from uuid import uuid4

from docx import Document
from pymongo import MongoClient, ReturnDocument
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.config.settings import settings
from app.services.data_loader import data_loader
from app.services.evidence_service import extract_evidence_text


class MongoAdvancedService:
    def __init__(self):
        if not settings.MONGODB_URL:
            raise RuntimeError("MONGODB_URL is not configured.")
        self.client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        self.db = self.client[settings.MONGODB_DATABASE]
        self.collections = {
            name: self.db[name]
            for name in (
                "court_listings",
                "court_backlog_snapshots",
                "court_notifications",
                "document_templates",
                "portal_documents",
                "signatures",
                "chronology_events",
                "dictations",
                "case_outcomes",
                "audit_logs",
            )
        }

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    def add_listing(self, organization_id, user_id, payload):
        record = payload.model_dump()
        record.update(
            {
                "_id": str(uuid4()),
                "organization_id": organization_id,
                "created_by": user_id,
                "created_at": self._now(),
            }
        )
        self.collections["court_listings"].insert_one(record)
        return self._clean(record)

    def list_listings(self, organization_id, matter_id=None):
        query = {"organization_id": organization_id}
        if matter_id:
            query["matter_id"] = matter_id
        return [self._clean(x) for x in self.collections["court_listings"].find(query).sort("hearing_date", 1)]

    def update_listing(self, organization_id, listing_id, updates):
        before = self.collections["court_listings"].find_one(
            {"_id": listing_id, "organization_id": organization_id}
        )
        if not before:
            return None
        updates = {key: value for key, value in updates.items() if value is not None}
        updates["updated_at"] = self._now()
        self.collections["court_listings"].update_one({"_id": listing_id}, {"$set": updates})
        return self._clean(self.collections["court_listings"].find_one({"_id": listing_id}))

    def sync_ndap_backlog(self, organization_id, user_id, state=None, case_type=None):
        """Synchronize the imported NDAP backlog into tenant-scoped snapshots."""
        frame = data_loader.court_backlog_data
        if frame is None:
            raise RuntimeError("NDAP_REPORT_7149.csv is not loaded.")
        rows = frame
        if state:
            rows = rows[rows["State"].astype(str).str.lower() == state.strip().lower()]
        if case_type:
            rows = rows[rows["Court case type"].astype(str).str.lower() == case_type.strip().lower()]

        inserted = 0
        updated = 0
        notifications = []
        for _, row in rows.iterrows():
            source_key = "|".join(
                str(row.get(column, ""))
                for column in ("State", "High court name", "High court bench", "Court case type", "Year")
            )
            snapshot = {
                "source_key": hashlib.sha256(source_key.encode("utf-8")).hexdigest(),
                "source": "NDAP_REPORT_7149.csv",
                "state": str(row.get("State", "")),
                "court": str(row.get("High court name", "")),
                "bench": str(row.get("High court bench", "")),
                "case_type": str(row.get("Court case type", "")),
                "year": int(row.get("Year", 0) or 0),
                "pending_cases": float(row.get("Pending cases in high court", 0) or 0),
                "instituted_last_month": float(row.get("Cases that were instituted in last month", 0) or 0),
                "disposed_last_month": float(row.get("Cases that were disposed in last month", 0) or 0),
                "synced_by": user_id,
                "synced_at": self._now(),
            }
            collection = self.collections["court_backlog_snapshots"]
            previous = collection.find_one(
                {"organization_id": organization_id, "source_key": snapshot["source_key"]}
            )
            if previous:
                changed = any(
                    previous.get(field) != snapshot.get(field)
                    for field in ("pending_cases", "instituted_last_month", "disposed_last_month")
                )
                collection.update_one(
                    {"_id": previous["_id"]},
                    {"$set": {**snapshot, "organization_id": organization_id}},
                )
                updated += 1
                if changed:
                    notification = {
                        "_id": str(uuid4()),
                        "organization_id": organization_id,
                        "type": "court_backlog_changed",
                        "source_key": snapshot["source_key"],
                        "message": (
                            f"Backlog changed for {snapshot['court']} "
                            f"({snapshot['case_type']}) in {snapshot['state']}."
                        ),
                        "created_at": self._now(),
                        "read": False,
                    }
                    self.collections["court_notifications"].insert_one(notification)
                    notifications.append(self._clean(notification))
            else:
                snapshot.update(
                    {
                        "_id": str(uuid4()),
                        "organization_id": organization_id,
                        "created_at": self._now(),
                    }
                )
                collection.insert_one(snapshot)
                inserted += 1

        return {
            "source": "NDAP_REPORT_7149.csv",
            "matched_rows": len(rows),
            "inserted": inserted,
            "updated": updated,
            "notifications_created": len(notifications),
            "notifications": notifications,
        }

    def list_court_notifications(self, organization_id, unread_only=False):
        query = {"organization_id": organization_id}
        if unread_only:
            query["read"] = False
        return [
            self._clean(item)
            for item in self.collections["court_notifications"].find(query).sort("created_at", -1)
        ]

    def mark_court_notification_read(self, organization_id, notification_id):
        result = self.collections["court_notifications"].find_one_and_update(
            {"_id": notification_id, "organization_id": organization_id},
            {"$set": {"read": True, "read_at": self._now()}},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            raise KeyError("Court notification was not found.")
        return self._clean(result)

    def create_template(self, organization_id, user_id, payload):
        record = payload.model_dump()
        record.update({"_id": str(uuid4()), "organization_id": organization_id, "created_by": user_id, "created_at": self._now()})
        self.collections["document_templates"].insert_one(record)
        return self._clean(record)

    def render_template(self, organization_id, payload):
        template = self.collections["document_templates"].find_one(
            {"_id": payload.template_id, "organization_id": organization_id}
        )
        if not template:
            raise KeyError("Document template was not found.")
        content = template["content"]
        for key, value in payload.values.items():
            content = content.replace("{{" + key + "}}", str(value))
        if payload.output_format == "pdf":
            output = io.BytesIO()
            pdf = canvas.Canvas(output, pagesize=A4)
            y = 800
            for line in content.splitlines() or [content]:
                pdf.drawString(40, y, line[:110])
                y -= 16
                if y < 40:
                    pdf.showPage()
                    y = 800
            pdf.save()
            return output.getvalue(), "application/pdf", f"{template['name']}.pdf"
        document = Document()
        for line in content.splitlines() or [content]:
            document.add_paragraph(line)
        output = io.BytesIO()
        document.save(output)
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{template['name']}.docx"

    def create_portal_document(self, organization_id, user_id, payload):
        raw = base64.b64decode(payload.content_base64)
        record = {
            "_id": str(uuid4()),
            "organization_id": organization_id,
            "uploaded_by": user_id,
            "name": payload.name,
            "mime_type": payload.mime_type,
            "content": raw,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "status": "pending_signature",
            "created_at": self._now(),
        }
        self.collections["portal_documents"].insert_one(record)
        record.pop("content")
        return self._clean(record)

    def list_portal_documents(self, organization_id):
        documents = self.collections["portal_documents"].find(
            {"organization_id": organization_id},
            {"content": 0},
        ).sort("created_at", -1)
        return [self._clean(document) for document in documents]

    def download_portal_document(self, organization_id, document_id):
        document = self.collections["portal_documents"].find_one(
            {"_id": document_id, "organization_id": organization_id},
            {"content": 1, "mime_type": 1, "name": 1},
        )
        if not document:
            raise KeyError("Portal document was not found.")
        return (
            document["content"],
            document.get("mime_type") or "application/octet-stream",
            document.get("name") or "portal-document",
        )

    def sign_document(self, organization_id, user_id, document_id, payload):
        document = self.collections["portal_documents"].find_one(
            {"_id": document_id, "organization_id": organization_id}
        )
        if not document:
            raise KeyError("Portal document was not found.")
        signed_at = self._now()
        signature_hash = hashlib.sha256(
            f"{document['sha256']}|{payload.signer_name}|{payload.signature_text}|{signed_at.isoformat()}".encode()
        ).hexdigest()
        signature = {
            "_id": str(uuid4()),
            "organization_id": organization_id,
            "document_id": document_id,
            "signed_by": user_id,
            "signer_name": payload.signer_name,
            "signer_email": payload.signer_email,
            "signature_text": payload.signature_text,
            "signature_hash": signature_hash,
            "signed_at": signed_at,
        }
        self.collections["signatures"].insert_one(signature)
        self.collections["portal_documents"].update_one({"_id": document_id}, {"$set": {"status": "signed"}})
        return self._clean(signature)

    def extract_chronology(self, organization_id, user_id, payload):
        events = []
        date_pattern = (
            r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
            r"(?:19|20)\d{2}[/-]\d{1,2}[/-]\d{1,2}|"
            r"(?:\d{1,2}(?:st|nd|rd|th)?[\s.-]+)?(?:Jan(?:uary)?|Feb(?:ruary)?|"
            r"Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
            r"Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
            r"[\s,.-]+(?:19|20)\d{2})\b"
        )
        for match in re.finditer(date_pattern, payload.text):
            start = max(0, match.start() - 140)
            end = min(len(payload.text), match.end() + 180)
            event = {
                "_id": str(uuid4()),
                "organization_id": organization_id,
                "matter_id": payload.matter_id,
                "date_text": match.group(0),
                "description": " ".join(payload.text[start:end].split()),
                "source": "text_ner",
                "event_type": self._event_type(payload.text[start:end]),
                "entities": self._entities(payload.text[start:end]),
                "created_by": user_id,
                "created_at": self._now(),
            }
            self.collections["chronology_events"].insert_one(event)
            events.append(self._clean(event))
        return events

    @staticmethod
    def _event_type(context: str) -> str:
        lowered = context.lower()
        if any(word in lowered for word in ("hearing", "court", "order", "judgment")):
            return "court_event"
        if any(word in lowered for word in ("filed", "petition", "complaint", "application")):
            return "filing"
        if any(word in lowered for word in ("arrest", "police", "fir", "investigation")):
            return "investigation"
        return "case_event"

    @staticmethod
    def _entities(context: str) -> list[str]:
        candidates = re.findall(r"\b[A-Z][A-Za-z.-]{2,}(?:\s+[A-Z][A-Za-z.-]{2,}){0,3}\b", context)
        return list(dict.fromkeys(candidates))[:10]

    def save_dictation(self, organization_id, user_id, transcript, source):
        sections = {
            "summary": transcript.strip()[:1000],
            "client_instructions": self._sentences(transcript, ["client", "must", "should"]),
            "court_directives": self._sentences(transcript, ["court", "judge", "hearing", "order"]),
            "action_items": self._sentences(transcript, ["action", "file", "submit", "prepare", "deadline"]),
        }
        record = {"_id": str(uuid4()), "organization_id": organization_id, "user_id": user_id, "transcript": transcript, **sections, "transcription_source": source, "created_at": self._now()}
        self.collections["dictations"].insert_one(record)
        cleaned = self._clean(record)
        cleaned["dictation_id"] = cleaned["id"]
        return cleaned

    def add_outcome(self, organization_id, user_id, payload):
        record = payload.model_dump()
        record.update({"_id": str(uuid4()), "organization_id": organization_id, "created_by": user_id, "created_at": self._now()})
        self.collections["case_outcomes"].insert_one(record)
        return self._clean(record)

    def analytics(self, organization_id, group_by):
        rows = list(self.collections["case_outcomes"].find({"organization_id": organization_id}))
        grouped = {}
        for row in rows:
            key = row.get(group_by) or "Unknown"
            group = grouped.setdefault(key, {"group": key, "cases": 0, "wins": 0, "settlements": 0, "resolution_days": []})
            group["cases"] += 1
            group["wins"] += int(str(row.get("outcome", "")).lower() in {"win", "won", "favorable"})
            group["settlements"] += int(bool(row.get("settlement")))
            if row.get("resolution_days") is not None:
                group["resolution_days"].append(row["resolution_days"])
        for group in grouped.values():
            days = group.pop("resolution_days")
            group["win_rate"] = round(group["wins"] / group["cases"] * 100, 2) if group["cases"] else 0
            group["settlement_rate"] = round(group["settlements"] / group["cases"] * 100, 2) if group["cases"] else 0
            group["average_resolution_days"] = round(sum(days) / len(days), 2) if days else None
        return list(grouped.values())

    def audit(self, organization_id, user_id, action, resource_type, resource_id, metadata=None):
        previous = self.collections["audit_logs"].find_one({"organization_id": organization_id}, sort=[("timestamp", -1)])
        previous_hash = previous["hash"] if previous else "GENESIS"
        timestamp = self._now()
        payload = f"{previous_hash}|{organization_id}|{user_id}|{action}|{resource_type}|{resource_id}|{timestamp.isoformat()}|{metadata or {}}"
        record = {"_id": str(uuid4()), "organization_id": organization_id, "user_id": user_id, "action": action, "resource_type": resource_type, "resource_id": resource_id, "metadata": metadata or {}, "previous_hash": previous_hash, "hash": hashlib.sha256(payload.encode()).hexdigest(), "timestamp": timestamp}
        self.collections["audit_logs"].insert_one(record)
        return self._clean(record)

    @staticmethod
    def _sentences(text, words):
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if any(word in sentence.lower() for word in words)][:10]

    @staticmethod
    def _clean(value):
        if isinstance(value, dict):
            value = dict(value)
            if "_id" in value:
                value["id"] = value.pop("_id")
            return {key: MongoAdvancedService._clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [MongoAdvancedService._clean(item) for item in value]
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bytes):
            return None
        return value
