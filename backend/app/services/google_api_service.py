"""Compatibility service for Gemini embeddings and shared Groq text generation."""
import os
import re
from app.config.settings import settings
from app.services.text_generation_service import TextGenerationError, TextGenerationService

try:
    from google import genai as google_genai
except ImportError:
    google_genai = None

from typing import Optional
import logging

logger = logging.getLogger(__name__)

class GoogleAPIClient:
    """Google API client for chatbot and AI features"""
    
    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None):
        """Initialize Google API client"""
        self.api_key = (
            settings.GOOGLE_API_KEY if api_key is None and settings.GOOGLE_API_KEY else api_key
        ) or (os.getenv("GOOGLE_API_KEY") if api_key is None else None)
        self.project_id = (
            settings.GOOGLE_PROJECT_ID if project_id is None else project_id
        ) or (os.getenv("GOOGLE_PROJECT_ID") if project_id is None else None)
        self.client = None
        self.text_generation = TextGenerationService()

        if self.api_key:
            if google_genai:
                try:
                    self.client = google_genai.Client(api_key=self.api_key)
                    logger.info("Google GenAI client configured")
                except Exception as exc:
                    logger.warning("Google GenAI client configuration failed: %s", exc)
        if not self.api_key or not self.client:
            logger.warning("Google GenAI is not configured.")

    @staticmethod
    def _service_error(detail: str) -> dict:
        return {
            "success": False,
            "error": "Text generation service unavailable",
            "detail": detail,
        }

    def generate_text(self, prompt: str, *, response_mime_type: str | None = None) -> str:
        return self.text_generation.generate(prompt, response_mime_type=response_mime_type)

    def generate_embedding(self, text: str) -> list[float]:
        if not text or not text.strip():
            return []
        if not self.api_key:
            raise RuntimeError("Please check the Gemini API configuration.")
        if not self.client:
            raise RuntimeError("The Google GenAI SDK is not installed or could not initialize.")
        response = self.client.models.embed_content(
            model=settings.GOOGLE_EMBEDDING_MODEL,
            contents=text,
        )
        embeddings = getattr(response, "embeddings", None) or []
        if not embeddings:
            raise RuntimeError("Gemini returned an empty embedding.")
        values = getattr(embeddings[0], "values", None)
        if not values:
            raise RuntimeError("Gemini returned an empty embedding.")
        return [float(value) for value in values]
    
    async def generate_chatbot_response(self, 
                                       query: str,
                                       context: Optional[str] = None,
                                       document_context: Optional[dict] = None,
                                       chat_history: Optional[list] = None) -> dict:
        """
        Generate legal chatbot response using Google Generative AI
        
        Args:
            query: User's legal question
            context: Additional context about the case
            document_context: Uploaded document data with 'text' and 'filename' keys
            
        Returns:
            dict with response and metadata
        """
        try:
            grounded_answer = self._answer_document_question(query, document_context)
            if grounded_answer:
                return {
                    "response": grounded_answer,
                    "source": "Case Document Analysis",
                    "verified": True,
                    "model": "grounded_extraction",
                    "status": "success",
                }

            system_prompt = """You are an expert legal advisor specialized in the Indian Judiciary system.
Provide accurate legal information based on:
- Indian Penal Code (IPC)
- Criminal Procedure Code (CrPC)
- Civil Procedure Code (CPC)
- Indian Constitution
- Relevant case law

CRITICAL RULES:
1. Always cite relevant sections with section numbers (e.g., "IPC Section 498A")
2. Provide clear, step-by-step explanations
3. Include a disclaimer: "This is general legal information. Please consult a qualified lawyer for specific advice."
4. Be accurate - only provide factual legal information
5. If unsure, state "I cannot provide a specific answer without more information"
6. Provide relevant examples from Indian legal context
7. Mention typical timelines and procedures
8. Treat the uploaded record as the source of truth. Do not invent facts, dates, parties, filings, or outcomes.
9. If the record does not answer the question, say exactly that and then provide general legal information separately.
10. When a prior question is supplied, answer the new question directly; do not repeat the previous answer.
"""

            full_prompt = f"{system_prompt}\n\nUser's Question: {query}"
            if context:
                full_prompt += f"\n\nAdditional Context: {context}"

            if document_context and document_context.get("text"):
                doc_text = document_context["text"][:8000]
                full_prompt += f"\n\nUploaded Document ({document_context.get('filename', 'document')}):\n{doc_text}"
                full_prompt += "\n\nAnswer the question based on the uploaded document content above."
            if chat_history:
                full_prompt += "\n\nPrevious conversation turns:\n" + "\n".join(
                    f"Q: {turn.get('question', '')}\nA: {turn.get('answer', '')}" for turn in chat_history[-6:]
                )

            model_name = settings.GROQ_MODEL
            text = self.generate_text(full_prompt)

            if document_context and self._is_unhelpful_document_answer(text, document_context["text"]):
                grounded_fallback = self._answer_document_question(query, document_context, force=True)
                if grounded_fallback:
                    return {
                        "response": grounded_fallback,
                        "source": "Case Document Analysis (Groq response corrected)",
                        "verified": True,
                        "model": "grounded_extraction",
                        "status": "corrected",
                    }

            return {
                "response": text,
                "source": "Groq",
                "verified": True,
                "model": model_name,
                "status": "success"
            }

        except (TextGenerationError, RuntimeError) as e:
            logger.error("Error generating chatbot response: %s", e)
            if document_context and document_context.get("text"):
                grounded_fallback = self._answer_document_question(query, document_context, force=True)
                if grounded_fallback:
                    return {
                        "response": grounded_fallback,
                        "source": "Case Document Analysis (Groq unavailable)",
                        "verified": True,
                        "model": "grounded_extraction",
                        "status": "grounded_only",
                    }
            return self._service_error(str(e))

    @staticmethod
    def _answer_document_question(query: str, document_context: Optional[dict], force: bool = False) -> Optional[str]:
        """Answer fact-retrieval questions from explicit document evidence before using a model."""
        if not document_context or not document_context.get("text"):
            return None
        query_lower = query.lower()
        discrepancy_question = any(term in query_lower for term in ["discrepanc", "contradict", "inconsisten", "mismatch", "different"])
        hearing_question = any(term in query_lower for term in ["last hearing", "in last hearing", "what happened in hearing", "what happen in hearing", "hearing happen"])
        closure_question = any(term in query_lower for term in ["case closed", "case close", "final order", "judgment date", "when did the case end"])
        if not force and not discrepancy_question and not hearing_question and not closure_question:
            return None

        text = document_context["text"]
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        date_pattern = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b"

        if hearing_question:
            hearing_lines = [line for line in lines if re.search(r"hearing|heard|appearance|adjourn|proceeding|order passed|matter was taken|next date", line, re.IGNORECASE)]
            if hearing_lines:
                selected = hearing_lines[-3:]
                return "The latest hearing-related entries I found in the uploaded record are:\n\n- " + "\n- ".join(selected) + "\n\nThis answer is limited to statements extracted from the uploaded case files."
            return "The uploaded case text does not contain a clear entry describing what happened at the last hearing. I cannot verify that event from the extracted record."

        if closure_question:
            closing_lines = [line for line in lines if re.search(r"final judgment|final order|case closed|disposed|disposal|judgment pronounced|matter concluded", line, re.IGNORECASE)]
            if closing_lines:
                return "The case-closing information found in the uploaded record is:\n\n- " + "\n- ".join(closing_lines[-3:]) + "\n\nThis is extracted from the case file; confirm it against the signed order."
            return "The uploaded record does not state a verified closure or final-order entry. I cannot identify a closing date from the extracted text."

        if not discrepancy_question:
            return None

        dates = re.findall(date_pattern, text, re.IGNORECASE)
        unique_dates = sorted({date.lower() for date in dates})
        signals = []
        for keyword in ["plaintiff", "petitioner", "defendant", "respondent", "judge", "court", "claim", "amount", "payment", "judgment", "order"]:
            mentions = [line for line in lines if keyword in line.lower()]
            if len(mentions) > 1 and len(set(mentions)) > 1:
                signals.append(f"{keyword.title()} appears in multiple different statements: {' | '.join(mentions[:2])}")
        if len(unique_dates) > 1 and any(term in text.lower() for term in ["filed", "order", "judgment", "hearing"]):
            signals.append(f"The record contains multiple dated events: {', '.join(unique_dates[:6])}.")
        if re.search(r"\bno\s+payment\b", text, re.IGNORECASE) and re.search(r"\bpayment\s+(?:was|has been)?\s*made\b", text, re.IGNORECASE):
            signals.append("Payment is described inconsistently: one statement says no payment was made, while another says payment was made.")
        if not signals:
            return "I did not find a confirmed discrepancy in the extracted case text. I found no conflicting party, amount, order, or date statements that could be verified automatically. Please identify the page or statement you want compared."
        return "Potential discrepancies found in the uploaded record:\n\n- " + "\n- ".join(signals) + "\n\nThese are document-level flags, not a final legal conclusion. Verify each item against the original page and filing."

    @staticmethod
    def _is_unhelpful_document_answer(answer: str, document_text: str) -> bool:
        normalized_answer = re.sub(r"[*_]", "", answer or "").lower().strip()
        if len(normalized_answer) < 80:
            return True
        generic_openers = ["based on the uploaded case record", "based on the case file", "i can help", "regarding your question"]
        return any(normalized_answer.startswith(opener) and len(normalized_answer) < 500 for opener in generic_openers)
    
    async def classify_legal_issue(self, text: str) -> dict:
        """Classify legal issue using AI"""
        try:
            prompt = f"""Analyze this legal case and classify:
            1. Case type (Criminal/Civil)
            2. Relevant sections of law
            3. Complexity level
            4. Estimated severity
            
            Case text: {text}"""
            return {
                "classification": self.generate_text(prompt),
                "source": "Groq",
                "success": True
            }

        except Exception as e:
            logger.error("Error classifying legal issue: %s", e)
            return self._service_error(str(e))
    
    async def extract_case_entities(self, text: str) -> dict:
        """Extract entities from case text"""
        try:
            prompt = f"""Extract legal entities from this text:
            - Case name
            - Parties involved
            - Relevant sections
            - Key dates
            - Relief sought
            
            Text: {text}"""
            return {
                "entities": self.generate_text(prompt),
                "success": True
            }

        except Exception as e:
            logger.error("Error extracting entities: %s", e)
            return self._service_error(str(e))
    
    @staticmethod
    def _get_mock_response(query: str, document_context: dict = None) -> dict:
        """Legacy compatibility helper; not used by provider-backed routes."""
        
        # Comprehensive legal knowledge base
        legal_kb = {
            "bail": {
                "keywords": ["bail", "bail application", "bail bond", "surety"],
                "response": "Bail Provisions in Indian Law:\n\n1. Bailable Offenses: Bail is a right (CrPC Section 436)\n2. Non-Bailable Offenses: Bail is at court's discretion (CrPC Section 437)\n3. Anticipatory Bail: Before arrest (CrPC Section 438)\n\nKey Factors:\n- Nature and gravity of the offense\n- Severity of punishment\n- Character and standing of the accused\n- Likelihood of fleeing justice\n- Risk of tampering with evidence\n\nBail Amount: Typically Rs 10,000 - Rs 5,00,000 depending on severity\n\nProcedure:\n1. File bail application in concerned court\n2. Provide surety and personal bond\n3. Court hearing within 7-14 days\n4. Conditions may include passport surrender, regular reporting"
            },
            "punishment": {
                "keywords": ["punishment", "sentence", "penalty", "jail", "imprisonment", "prison", "punish", "convicted", "guilty", "proven guilty"],
                "response": "Punishments Under Indian Penal Code:\n\nTypes of Punishment (IPC Section 53):\n1. Death Penalty - Rarest cases (murder, terrorism)\n2. Life Imprisonment - Serious offenses (murder, kidnapping)\n3. Rigorous Imprisonment - With hard labor\n4. Simple Imprisonment - Without hard labor\n5. Fine - Monetary penalty\n6. Forfeiture of Property\n\nCommon Offense Punishments:\n- IPC 302 (Murder): Death or life imprisonment + fine\n- IPC 376 (Rape): 10 years to life imprisonment\n- IPC 420 (Cheating): Up to 7 years + fine\n- IPC 304 (Culpable Homicide): Up to 10 years + fine\n- IPC 498A (Cruelty): Up to 3 years + fine\n- IPC 406 (Criminal Breach of Trust): Up to 3 years + fine\n- IPC 120B (Criminal Conspiracy): Same as the offense conspired\n\nMitigating Factors that reduce sentence:\n- First-time offender\n- Age (juvenile/elderly)\n- Cooperation with investigation\n- Provocation or self-defense\n- Good character and standing"
            },
            "evidence": {
                "keywords": ["evidence", "proof", "witness", "testimony", "forensic", "admissible"],
                "response": "Evidence in Indian Law (Indian Evidence Act, 1872):\n\nTypes of Evidence:\n1. Documentary Evidence (Section 3)\n   - Public documents, private documents\n   - Electronic records (Section 65B, IT Act)\n\n2. Oral Evidence (Section 59-60)\n   - Direct testimony of witnesses\n   - Expert opinions\n\n3. Physical/Material Evidence\n   - Forensic evidence (DNA, fingerprints)\n   - Weapons, objects at crime scene\n\n4. Circumstantial Evidence\n   - Chain of circumstances pointing to guilt\n   - Must form a complete chain (Sharad Birdhichand case)\n\nBurden of Proof:\n- Prosecution must prove guilt beyond reasonable doubt\n- In civil cases: preponderance of probability\n\nImportant Rules:\n- Hearsay is generally inadmissible (Section 60)\n- Confession to police is not admissible (Section 25)\n- Dying declaration is admissible (Section 32)\n- Electronic evidence needs Section 65B certificate"
            },
            "fir": {
                "keywords": ["fir", "first information report", "police complaint", "lodge complaint", "file complaint"],
                "response": "Filing FIR (First Information Report):\n\nProcedure (CrPC Section 154):\n1. Visit police station with jurisdiction\n2. Provide details orally or in writing\n3. Police must register FIR - it is mandatory for cognizable offenses\n4. Get FIR copy free of cost (Section 154(2))\n\nIf Police Refuses:\n- Complaint to Superintendent of Police\n- Complaint to Magistrate (Section 156(3))\n- File private complaint (Section 200)\n\nTimeline: FIR should be filed immediately\nZero FIR: Can be filed at any police station regardless of jurisdiction\n\nOnline FIR: Available in many states via state police websites"
            },
            "appeal": {
                "keywords": ["appeal", "high court", "supreme court", "revision", "review", "challenge"],
                "response": "Appeals in Indian Legal System:\n\n1. First Appeal:\n   - District Court → High Court\n   - Sessions Court → High Court\n   - As a matter of right in most cases\n\n2. Second Appeal (Section 100 CPC):\n   - High Court → Supreme Court\n   - Only on substantial questions of law\n\n3. Special Leave Petition (Article 136):\n   - To Supreme Court from any court/tribunal\n   - Discretionary power of Supreme Court\n\n4. Criminal Appeals:\n   - Against conviction: as of right\n   - Against acquittal: by State (requires leave)\n\nTimeline for Filing:\n- Criminal appeal: 30-90 days from judgment\n- Civil appeal: 30-90 days\n- SLP: 90 days from High Court order\n\nStay of Execution: Court may grant stay pending appeal"
            },
            "rights": {
                "keywords": ["rights", "fundamental rights", "accused rights", "my rights", "legal rights", "constitutional"],
                "response": "Fundamental & Legal Rights:\n\nConstitutional Rights:\n- Right to Equality (Article 14)\n- Right to Life & Liberty (Article 21)\n- Protection against self-incrimination (Article 20(3))\n- Right to legal representation (Article 22)\n- Protection against double jeopardy (Article 20(2))\n\nRights of Accused:\n- Presumption of innocence until proven guilty\n- Right to know grounds of arrest (Section 50 CrPC)\n- Right to be produced before magistrate within 24 hours\n- Right to bail in bailable offenses\n- Right to free legal aid (Article 39A)\n- Right to speedy trial\n- Right to cross-examine witnesses\n- Right to appeal conviction"
            },
            "divorce": {
                "keywords": ["divorce", "separation", "marriage", "alimony", "maintenance", "custody", "matrimonial"],
                "response": "Divorce Laws in India:\n\nGrounds for Divorce (Hindu Marriage Act Section 13):\n- Adultery, Cruelty, Desertion (2+ years)\n- Mental disorder, Communicable disease\n- Mutual consent (Section 13B) - after 1 year separation\n\nMutual Consent Divorce:\n- 6-18 months cooling period\n- Both parties agree on terms\n\nMaintenance:\n- Wife can claim interim maintenance (Section 24 HMA)\n- Permanent alimony (Section 25 HMA)\n- Children maintenance (Section 26 HMA)\n\nChild Custody:\n- Best interest of child is paramount\n- Generally mother gets custody of children under 5\n- Father's visiting rights are usually granted"
            },
            "property": {
                "keywords": ["property", "land", "real estate", "title", "ownership", "transfer", "possession", "tenant", "lease"],
                "response": "Property Laws in India:\n\nKey Legislation:\n- Transfer of Property Act, 1882\n- Registration Act, 1908\n- Indian Easement Act, 1882\n\nProperty Transfer:\n- Sale deed must be registered (Section 17, Registration Act)\n- Stamp duty varies by state (3-10%)\n\nProperty Disputes:\n- Title verification through encumbrance certificate\n- Adverse possession: 12 years for private, 30 for government\n- Partition suit for joint property\n\nTenant Rights:\n- Rent Control Act provides protection\n- Eviction only through due process\n- Fair rent determination by court"
            },
            "timeline": {
                "keywords": ["timeline", "how long", "duration", "time", "years", "months", "delay"],
                "response": "Typical Case Timelines in Indian Courts:\n\nCriminal Cases:\n- Investigation: 2-4 months\n- Chargesheet filing: 60-90 days\n- Trial proceedings: 1-3 years\n- Appeals: 1-5 years\n\nCivil Cases:\n- Filing to first hearing: 1-3 months\n- Evidence stage: 6-18 months\n- Arguments: 2-6 months\n- Total: 2-5 years (may extend longer)\n\nFamily Courts: 6 months - 2 years\nConsumer Courts: 3-12 months\nLabour Courts: 1-3 years\n\nSupreme Court: 3-10 years for final disposal"
            },
            "contract": {
                "keywords": ["contract", "agreement", "breach", "obligation", "promise", "consideration"],
                "response": "Contract Law (Indian Contract Act, 1872):\n\nEssentials of Valid Contract:\n1. Offer and acceptance\n2. Free consent (Section 14)\n3. Lawful consideration (Section 23)\n4. Competency of parties (Section 11)\n5. Lawful object\n\nBreach of Contract Remedies:\n- Damages (Section 73-75)\n- Specific performance\n- Injunction\n- Rescission\n\nVoid vs Voidable:\n- Void: No legal effect from beginning\n- Voidable: Valid until avoided by aggrieved party"
            },
            "rape": {
                "keywords": ["rape", "sexual assault", "sexual offense", "376", "pocso", "molestation", "sexual harassment", "outraging modesty"],
                "response": "Rape & Sexual Offenses Under Indian Law:\n\nKey Sections:\n• IPC Section 375/376 — Rape: Minimum 10 years RI, extendable to life imprisonment + fine\n• IPC Section 376(2) — Aggravated Rape (by police/public servant/gang rape): Minimum 20 years RI to life or death\n• IPC Section 376AB — Rape of girl under 12: Minimum 20 years RI to life or death\n• IPC Section 354 — Assault/outraging modesty: 1-5 years + fine\n• IPC Section 354A — Sexual Harassment: Up to 3 years + fine\n• IPC Section 354D — Stalking: Up to 3 years (first), 5 years (repeat)\n• POCSO Act — Any sexual offense against child under 18: 3 years to life\n\nVictim Protections:\n1. Statement recorded by female officer or magistrate (Section 164 CrPC)\n2. In-camera trial mandatory (Section 327(2) CrPC)\n3. Identity of victim cannot be disclosed (Section 228A IPC)\n4. Medical examination within 24 hours\n5. Free legal aid to victim\n6. No two-finger test allowed (Lillu v State of Haryana)\n\nFIR & Investigation:\n- Zero FIR can be filed at ANY police station\n- Police MUST register FIR — refusal is punishable\n- Investigation to be completed in 2 months\n- Chargesheet within 60 days\n\nLandmark Cases:\n- Mukesh v State (Nirbhaya Case, 2017) — Death penalty for gang rape + murder\n- Tukaram v State of Maharashtra (Mathura Case) — Led to amendment of rape laws\n- Vishaka v State of Rajasthan — Sexual harassment guidelines"
            },
            "murder": {
                "keywords": ["murder", "homicide", "killing", "302", "304", "culpable homicide", "death caused"],
                "response": "Murder & Homicide Under Indian Law:\n\nKey Sections:\n• IPC Section 300/302 — Murder: Death penalty or life imprisonment + fine\n• IPC Section 304 — Culpable Homicide not amounting to Murder: Up to 10 years or life\n• IPC Section 304A — Death by Negligence: Up to 2 years + fine\n• IPC Section 304B — Dowry Death: Minimum 7 years, extendable to life\n• IPC Section 307 — Attempt to Murder: Up to 10 years + fine (life if hurt caused)\n• IPC Section 308 — Attempt to Culpable Homicide: Up to 3 years or 7 years\n\nMurder vs Culpable Homicide:\n- Murder (Sec 300): Intention to cause death OR knowledge that act will cause death\n- Culpable Homicide (Sec 299): Without premeditation, in sudden fight or provocation\n\nInvestigation Process:\n1. FIR registration → Inquest under Section 174 CrPC\n2. Post-mortem examination mandatory\n3. Scene of crime preservation\n4. Forensic evidence (DNA, ballistics, fingerprints)\n5. Witness statements under Section 161 CrPC\n\nBail: Generally NOT granted for IPC 302 (non-bailable offense)\n\nLandmark Cases:\n- K.M. Nanavati v State of Maharashtra — Culpable homicide vs murder\n- Machhi Singh v State of Punjab — Death penalty 'rarest of rare' doctrine\n- Bachan Singh v State of Punjab — Framework for death sentence"
            },
            "dowry": {
                "keywords": ["dowry", "498a", "498", "dowry death", "cruelty", "harassment by husband", "demand"],
                "response": "Dowry Laws in India:\n\nKey Sections:\n• IPC Section 498A — Cruelty by husband/relatives: Up to 3 years + fine (cognizable, non-bailable)\n• IPC Section 304B — Dowry Death: Minimum 7 years, up to life imprisonment\n• Dowry Prohibition Act, 1961:\n  - Section 3: Giving or taking dowry — 5 years + Rs 15,000 fine\n  - Section 4: Demand of dowry — 6 months to 2 years + fine\n\nDowry Death (Section 304B):\n- Death within 7 years of marriage\n- Evidence of cruelty/harassment for dowry\n- Burden shifts to husband's family to prove innocence\n\nFiling Complaint:\n1. Lodge FIR at nearest police station\n2. Complaint to Protection Officer under DV Act\n3. Application to Magistrate under Section 12, DV Act\n\nProtection of Women from Domestic Violence Act, 2005:\n- Protection orders, residence orders\n- Monetary relief and compensation\n- Custody orders for children\n\nLandmark Cases:\n- Arnesh Kumar v State of Bihar — Guidelines for arrest under 498A\n- Rajesh Sharma v State of UP — Safeguards against misuse of 498A"
            },
            "cyber": {
                "keywords": ["cyber", "online fraud", "hacking", "identity theft", "cyber crime", "it act", "phishing", "online"],
                "response": "Cyber Crime Laws in India (IT Act 2000, amended 2008):\n\nKey Offenses & Penalties:\n• Section 43 — Unauthorized computer access: Compensation up to Rs 5 crore\n• Section 65 — Computer source code tampering: 3 years + Rs 2 lakh fine\n• Section 66 — Computer hacking: 3 years + Rs 5 lakh fine\n• Section 66B — Receiving stolen computer resource: 3 years + Rs 1 lakh fine\n• Section 66C — Identity theft: 3 years + Rs 1 lakh fine\n• Section 66D — Cheating by impersonation using computer: 3 years + Rs 1 lakh\n• Section 66E — Violation of privacy: 3 years + Rs 2 lakh fine\n• Section 66F — Cyber terrorism: Life imprisonment\n• Section 67 — Publishing obscene content: 5 years + Rs 10 lakh fine\n• Section 67A — Sexually explicit content: 7 years + Rs 10 lakh fine\n• Section 67B — Child pornography: 7 years + Rs 10 lakh fine\n\nFiling Cyber Crime Complaint:\n1. National Cyber Crime Portal: cybercrime.gov.in\n2. Local police station (Cyber Cell)\n3. Preserve evidence: screenshots, URLs, transaction IDs\n\nJurisdiction: Where the victim is located OR where the server is"
            },
            "cheating": {
                "keywords": ["cheating", "fraud", "420", "dishonesty", "deception", "scam", "swindle", "misrepresentation"],
                "response": "Cheating & Fraud Under Indian Law:\n\nKey Sections:\n• IPC Section 415/420 — Cheating and dishonestly inducing delivery of property: Up to 7 years + fine\n• IPC Section 406 — Criminal breach of trust: Up to 3 years + fine\n• IPC Section 409 — Criminal breach of trust by public servant/banker: Up to life + fine\n• IPC Section 463/465 — Forgery: Up to 2 years + fine\n• IPC Section 467 — Forgery of valuable security: Up to life + fine\n• IPC Section 468 — Forgery for purpose of cheating: Up to 7 years + fine\n• IPC Section 471 — Using forged document: Same as making forged document\n\nEssential Elements of Cheating (Sec 415):\n1. Deception of any person\n2. Fraudulent or dishonest intent\n3. Inducing the deceived person to deliver property or to do/omit something\n4. The person would not have done so without being deceived\n\nEvidence Required:\n- Documentary proof of false promises/representations\n- Bank statements, transaction records\n- Communication records (emails, messages, letters)\n- Witness statements\n\nProcedure:\n1. File FIR under Section 420 IPC\n2. Criminal complaint before Magistrate under Section 200 CrPC\n3. Civil suit for recovery of money/property simultaneously possible"
            },
            "kidnapping": {
                "keywords": ["kidnapping", "abduction", "missing", "ransom", "363", "364", "hostage"],
                "response": "Kidnapping & Abduction Under Indian Law:\n\nKey Sections:\n• IPC Section 359-369 — Kidnapping provisions\n• IPC Section 363 — Kidnapping: Up to 7 years + fine\n• IPC Section 364 — Kidnapping for murder: Life imprisonment + fine\n• IPC Section 364A — Kidnapping for ransom: Death or life imprisonment\n• IPC Section 366 — Kidnapping woman to compel marriage: Up to 10 years + fine\n• IPC Section 366A — Procuration of minor girl: Up to 10 years + fine\n• IPC Section 369 — Kidnapping child under 10 for stealing: Up to 7 years + fine\n\nKidnapping vs Abduction:\n- Kidnapping: Taking minor (under 16 boy/18 girl) from lawful guardian\n- Abduction: Compelling/inducing any person to go from any place by force or deceit\n\nImmediate Steps:\n1. File FIR immediately — police MUST register\n2. Missing person report with photograph\n3. Police to act within 24 hours for children/women\n4. Free legal aid available"
            },
            "domestic": {
                "keywords": ["domestic violence", "domestic abuse", "protection order", "dv act", "wife beating", "cruelty wife"],
                "response": "Domestic Violence Act, 2005 — Complete Guide:\n\nWho Can File:\n- Wife, live-in partner, sister, mother, or any woman in domestic relationship\n\nTypes of Abuse Covered:\n1. Physical abuse — hitting, beating, slapping\n2. Emotional abuse — insults, ridicule, threats\n3. Sexual abuse — forced sexual intercourse\n4. Economic abuse — denying money, resources, employment\n\nRemedies Available:\n• Protection Order (Sec 18) — Restraining respondent from abuse\n• Residence Order (Sec 19) — Right to live in shared household\n• Monetary Relief (Sec 20) — Compensation, maintenance, medical expenses\n• Custody Order (Sec 21) — Temporary custody of children\n• Compensation Order (Sec 22) — For injuries and mental torture\n\nProcedure:\n1. Complaint to Protection Officer, police, or Magistrate\n2. Application under Section 12 before Magistrate\n3. Court must hear application within 3 days\n4. Order within 60 days\n\nAlso Under IPC:\n• Section 498A — Cruelty by husband/relatives: Up to 3 years + fine\n• Section 304B — Dowry death: 7 years to life"
            },
            "consumer": {
                "keywords": ["consumer", "product", "defective", "service", "complaint consumer", "refund", "warranty", "deficiency"],
                "response": "Consumer Protection Act, 2019:\n\nWho is a Consumer:\n- Anyone who buys goods/services for personal use (not for resale)\n\nGrounds for Complaint:\n1. Defective goods\n2. Deficiency in service\n3. Unfair trade practice\n4. Restrictive trade practice\n5. Overcharging beyond MRP\n\nConsumer Forums:\n• District Commission: Claims up to Rs 1 crore\n• State Commission: Rs 1 crore to Rs 10 crore\n• National Commission: Above Rs 10 crore\n\nFiling Complaint:\n1. Written complaint with documents (bill, warranty card, correspondence)\n2. No court fee required (free filing)\n3. File within 2 years from cause of action\n4. Can file online at edaakhil.nic.in\n5. No lawyer required — can argue yourself\n\nRemedies:\n- Replacement/refund of goods\n- Compensation for loss/injury\n- Removal of deficiency in service\n- Punitive damages for negligence\n\nTimeline: Disposal within 3-5 months (ideally)"
            },
        }
        
        query_lower = query.lower().strip()
        
        # If document context is available, use it to ENRICH the response
        doc_summary = ""
        doc_sections = []
        doc_case_type = ""
        if document_context and document_context.get("text"):
            doc_text = document_context["text"][:5000]
            filename = document_context.get("filename", "document")
            doc_lower = doc_text.lower()
            
            # Extract case context from document (sections, case type, etc.)
            section_patterns = [
                "ipc", "crpc", "cpc", "article", "section", "act",
                "prevention of corruption", "ndps", "it act", "arms act",
                "hindu marriage", "transfer of property", "evidence act",
                "companies act", "negotiable instruments", "motor vehicles"
            ]
            for pattern in section_patterns:
                if pattern in doc_lower:
                    # Extract the surrounding context
                    idx = doc_lower.find(pattern)
                    start = max(0, idx - 5)
                    end = min(len(doc_text), idx + 40)
                    snippet = doc_text[start:end].strip()
                    # Clean up to get just the section reference
                    for line in snippet.split('\n'):
                        line = line.strip()
                        if pattern in line.lower() and len(line) < 60:
                            doc_sections.append(line)
            doc_sections = list(set(doc_sections))[:8]
            
            # Detect case type from document
            case_types = {
                "criminal": ["murder", "theft", "robbery", "assault", "ipc", "crpc", "fir", "accused", "prosecution", "conviction", "bail"],
                "civil": ["plaintiff", "defendant", "damages", "injunction", "suit", "cpc", "decree"],
                "family": ["divorce", "custody", "maintenance", "marriage", "alimony", "matrimonial"],
                "property": ["property", "land", "title", "possession", "transfer", "lease", "tenant", "eviction"],
                "commercial": ["company", "corporate", "contract", "arbitration", "trademark", "partnership"],
            }
            for ctype, keywords in case_types.items():
                matches = sum(1 for kw in keywords if kw in doc_lower)
                if matches >= 2:
                    doc_case_type = ctype
                    break
            
            # Build a brief document summary
            sentences = [s.strip() for s in doc_text.replace('\n', '. ').split('. ') if len(s.strip()) > 15]
            key_sentences = sentences[:5]
            if key_sentences:
                doc_summary = " ".join(key_sentences)
                if len(doc_summary) > 500:
                    doc_summary = doc_summary[:500] + "..."
        
        # STEP 1: Find BEST legal knowledge match (score all topics, pick highest)
        # Specific crime topics should win over generic topics like "punishment"
        legal_response = None
        matched_topic = None
        topic_scores = {}
        specific_topics = {"rape", "murder", "dowry", "kidnapping", "cheating", "cyber", "domestic", "consumer"}
        for topic, data in legal_kb.items():
            score = 0
            for kw in data["keywords"]:
                if kw in query_lower:
                    score += len(kw)
            if score > 0:
                # Boost specific crime topics so they win over generic ones
                if topic in specific_topics:
                    score += 50
                topic_scores[topic] = score
        
        if topic_scores:
            best_topic = max(topic_scores, key=topic_scores.get)
            legal_response = legal_kb[best_topic]["response"]
            matched_topic = best_topic
        
        # STEP 2: If no direct match, try to infer from document context
        if not legal_response and doc_case_type:
            # Map case type to likely relevant topics
            case_type_topics = {
                "criminal": "punishment",
                "civil": "contract",
                "family": "divorce",
                "property": "property",
                "commercial": "contract",
            }
            fallback_topic = case_type_topics.get(doc_case_type, None)
            if fallback_topic and fallback_topic in legal_kb:
                legal_response = legal_kb[fallback_topic]["response"]
                matched_topic = fallback_topic
        
        # STEP 3: Build final response
        if document_context and document_context.get("text"):
            filename = document_context.get("filename", "document")
            response_parts = []
            
            # Context header
            if doc_summary:
                response_parts.append(f"Based on your case document ({filename}):\n")
                if doc_case_type:
                    response_parts.append(f"Case Type Detected: {doc_case_type.title()}\n")
                if doc_sections:
                    response_parts.append(f"Relevant Sections: {', '.join(doc_sections[:5])}\n")
            
            # Main legal answer
            if legal_response:
                response_parts.append(f"\n{legal_response}")
            else:
                # General knowledgeable response for any question
                response_parts.append(f"\nRegarding your question about '{query}':\n")
                if doc_case_type == "criminal":
                    response_parts.append("Based on the criminal case in your document:\n\n")
                    response_parts.append("Key Legal Considerations:\n")
                    response_parts.append("1. The prosecution must prove guilt beyond reasonable doubt\n")
                    response_parts.append("2. The accused has the right to fair trial and legal representation\n")
                    response_parts.append("3. All evidence must be admissible under the Indian Evidence Act, 1872\n")
                    response_parts.append("4. The court will consider both aggravating and mitigating circumstances\n")
                    response_parts.append("5. Sentencing depends on the specific IPC sections charged\n\n")
                    if doc_sections:
                        response_parts.append(f"The sections mentioned in your document ({', '.join(doc_sections[:3])}) carry specific penalties as defined under IPC.\n\n")
                elif doc_case_type == "civil":
                    response_parts.append("Based on the civil matter in your document:\n\n")
                    response_parts.append("Key Legal Considerations:\n")
                    response_parts.append("1. Burden of proof is on the plaintiff (preponderance of probability)\n")
                    response_parts.append("2. Relief may include damages, injunction, or specific performance\n")
                    response_parts.append("3. Limitation period applies (Limitation Act, 1963)\n")
                    response_parts.append("4. Alternative dispute resolution (mediation/arbitration) may be available\n")
                elif doc_case_type == "family":
                    response_parts.append("Based on the family matter in your document:\n\n")
                    response_parts.append("Key Considerations:\n")
                    response_parts.append("1. Family courts have exclusive jurisdiction\n")
                    response_parts.append("2. Mediation is mandatory before trial\n")
                    response_parts.append("3. Best interest of child is paramount in custody matters\n")
                    response_parts.append("4. Maintenance rights are protected under law\n")
                else:
                    response_parts.append("Key Legal Analysis:\n")
                    response_parts.append("1. The applicable laws depend on the specific facts and jurisdiction\n")
                    response_parts.append("2. Both statutory provisions and case precedents will be considered\n")
                    response_parts.append("3. The court will evaluate evidence from both parties\n")
                    response_parts.append("4. Remedies available depend on the nature of the dispute\n")
                    if doc_sections:
                        response_parts.append(f"\nThe document references: {', '.join(doc_sections[:4])}\n")
            
            response_parts.append("\n\nDisclaimer: This is AI-assisted legal information. Please consult a qualified attorney for advice specific to your case.")
            
            return {
                "response": "".join(response_parts),
                "source": f"Legal Knowledge Base + Document ({filename})",
                "verified": True,
                "model": "hybrid_analysis"
            }
        
        # No document context — standard legal QA
        if legal_response:
            return {
                "response": legal_response,
                "source": "Legal Knowledge Base",
                "verified": True,
                "model": "mock"
            }
        
        return {
            "response": f"Regarding your question: '{query}'\n\nThis is a complex legal matter. Based on Indian legal framework:\n\n1. The specific provisions applicable depend on the facts of your case\n2. Multiple legal sections may be relevant including IPC, CrPC, CPC\n3. Timeline and procedures vary by jurisdiction and court level\n4. Both statutory law and judicial precedents will apply\n\nFor accurate guidance specific to your situation, please consult a qualified attorney.\n\nDisclaimer: This is general legal information, not legal advice.",
            "source": "Legal Knowledge Base",
            "verified": True,
            "model": "mock"
        }
    
    @staticmethod
    def _mock_classification() -> dict:
        """Mock classification response"""
        return {
            "classification": "Case Type: Criminal, Relevant Sections: IPC 406, Complexity: Medium, Severity: High",
            "source": "Mock AI",
            "success": True
        }
    
    @staticmethod
    def _mock_entity_extraction() -> dict:
        """Mock entity extraction"""
        return {
            "entities": {
                "case_name": "Case Name Not Available",
                "parties": [],
                "sections": [],
                "dates": [],
                "relief": "Not specified"
            },
            "success": True
        }
