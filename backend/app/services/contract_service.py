"""Contract extraction, risk analysis, and DOCX redlining."""

import io
import json
import logging
import re
from datetime import datetime
from uuid import uuid4

from pymongo import MongoClient
from docx import Document
from docx.shared import RGBColor

from app.config.settings import settings
from app.models.schemas import ContractRiskFlag
from app.services.text_generation_service import TextGenerationService

logger = logging.getLogger(__name__)


class ContractService:
    """Process contracts without changing the existing risk detector."""

    def __init__(self):
        self.documents = {}
        self.text_generation = TextGenerationService()
        self.collection = None
        if (
            settings.ENABLE_LEGALTECH_PERSISTENCE
            and settings.DATABASE_BACKEND.lower() == "mongo"
        ):
            if not settings.MONGODB_URL:
                raise RuntimeError("MONGODB_URL is not configured.")
            client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
            self.collection = client[settings.MONGODB_DATABASE]["contract_analyses"]
            self.collection.create_index(
                [("organization_id", 1), ("created_at", -1)]
            )

    @staticmethod
    def extract_text(filename: str, content: bytes) -> tuple[str, str]:
        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if suffix == "docx":
            document = Document(io.BytesIO(content))
            return "\n".join(p.text for p in document.paragraphs if p.text.strip()), "docx"
        if suffix == "pdf":
            try:
                import fitz

                document = fitz.open(stream=content, filetype="pdf")
                text = "\n".join(page.get_text("text") for page in document)
                document.close()
                if text.strip():
                    return text, "pdf"
            except ImportError:
                pass
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages), "pdf"
        raise ValueError("Only .pdf and .docx contract files are supported.")

    @staticmethod
    def _heuristic_flags(text: str) -> list[ContractRiskFlag]:
        playbook = [
            (
                r"auto(?:matic|matically)?\s+renew|evergreen",
                "Automatic renewal",
                "high",
                "The clause may renew the agreement without a fresh affirmative consent.",
                "Require written notice and affirmative renewal consent at least 30 days before expiry.",
            ),
            (
                r"unlimited\s+liability|liable\s+for\s+all\s+loss",
                "Unlimited liability",
                "high",
                "The clause appears to create uncapped exposure.",
                "Cap aggregate liability at fees paid in the prior 12 months, with narrowly defined carve-outs.",
            ),
            (
                r"indemnif(?:y|ication)|hold\s+harmless",
                "Indemnity",
                "medium",
                "The indemnity may transfer broad third-party or direct-loss exposure.",
                "Limit indemnity to third-party claims caused by the indemnifying party's breach, negligence, or misconduct.",
            ),
            (
                r"terminate\s+at\s+any\s+time|termination\s+for\s+convenience",
                "Termination for convenience",
                "medium",
                "A party may terminate without a stated notice or transition period.",
                "Add written notice, cure/transition obligations, and payment for committed services.",
            ),
            (
                r"governing\s+law|exclusive\s+jurisdiction",
                "Governing law and forum",
                "low",
                "The selected law or forum can materially affect enforcement cost and dispute strategy.",
                "Confirm the governing law and forum are commercially acceptable and mutually agreed.",
            ),
            (
                r"confidential(?:ity)?|non[-\s]disclosure",
                "Confidentiality",
                "low",
                "Confidentiality obligations should define exclusions, duration, and permitted disclosures.",
                "Add standard exclusions, compelled-disclosure procedure, and a defined survival period.",
            ),
        ]
        flags = []
        for pattern, clause, level, reason, revision in playbook:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(
                    ContractRiskFlag(
                        clause=clause,
                        risk_level=level,
                        reason=reason,
                        suggested_revision=revision,
                    )
                )
        return flags

    def _llm_flags(self, text: str) -> list[ContractRiskFlag]:
        if not settings.GROQ_API_KEY:
            return []
        prompt = f"""You are a contract risk reviewer. Return only a JSON array.
Each item must contain exactly: clause, risk_level, reason, suggested_revision.
risk_level must be one of: low, medium, high.
Do not invent clauses absent from the contract.

Contract:
{text[:18000]}
"""
        raw = self.text_generation.generate(prompt, response_mime_type="application/json")
        parsed = json.loads(raw)
        return [ContractRiskFlag.model_validate(item) for item in parsed]

    def analyze(
        self,
        *,
        filename: str,
        content: bytes,
        organization_id: str,
        user_id: str,
    ) -> dict:
        text, source_type = self.extract_text(filename, content)
        flags = self._llm_flags(text)
        source = "groq_playbook"

        analysis_id = str(uuid4())
        record = {
            "_id": analysis_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "filename": filename,
            "text": text,
            "source_type": source_type,
            "flags": [flag.model_dump() for flag in flags],
            "created_at": datetime.utcnow(),
        }
        if self.collection is not None:
            self.collection.insert_one(record)
        else:
            self.documents[analysis_id] = record
        return {
            "analysis_id": analysis_id,
            "filename": filename,
            "source_type": source_type,
            "extracted_characters": len(text),
            "flags": [flag.model_dump() for flag in flags],
            "analysis_source": source,
        }

    def redline(
        self,
        analysis_id: str,
        *,
        organization_id: str,
        user_id: str,
    ) -> tuple[bytes, str]:
        if self.collection is not None:
            record = self.collection.find_one(
                {
                    "_id": analysis_id,
                    "organization_id": organization_id,
                    "user_id": user_id,
                }
            )
        else:
            record = self.documents.get(analysis_id)
            if record and (
                record["organization_id"] != organization_id
                or record["user_id"] != user_id
            ):
                record = None
        if not record:
            raise KeyError("Contract analysis was not found.")
        document = Document()
        document.add_heading("Nyay AI Contract Risk Review", level=1)
        document.add_paragraph(f"Source: {record['filename']}")
        document.add_paragraph("Suggested revisions are appended in red and require legal review.")
        for paragraph_text in record["text"].splitlines():
            if not paragraph_text.strip():
                continue
            document.add_paragraph(paragraph_text)
        if record["flags"]:
            document.add_heading("Suggested Revisions", level=2)
            for flag_data in record["flags"]:
                flag = ContractRiskFlag.model_validate(flag_data)
                revision = document.add_paragraph()
                run = revision.add_run(
                    f"[{flag.risk_level.upper()}] {flag.clause}: "
                    f"{flag.suggested_revision}"
                )
                run.font.color.rgb = RGBColor(0xB0, 0x00, 0x20)
        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue(), f"nyay_ai_redline_{analysis_id}.docx"
