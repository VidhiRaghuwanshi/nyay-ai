"""Auto Drafting Service — Uses real precedent data for citations"""
import logging
from typing import Dict, Any, List, Tuple
import io
import base64
from datetime import datetime

# Try importing reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger = logging.getLogger(__name__)
    logger.warning("reportlab not installed. PDF generation disabled. Install with: pip install reportlab")

logger = logging.getLogger(__name__)


class AutoDraftingService:
    """Service for generating legal documents with real precedent citations"""
    
    TEMPLATES = {
        "petition": {
            "title": "PETITION UNDER SECTION 482 OF CRIMINAL PROCEDURE CODE, 1973",
            "sections": ["preamble", "facts", "legal_arguments", "relief"]
        },
        "bail": {
            "title": "BAIL APPLICATION",
            "sections": ["preamble", "eligibility", "facts", "legal_grounds", "relief"]
        },
        "fir": {
            "title": "FIRST INFORMATION REPORT",
            "sections": ["header", "incident_details", "accused_description", "investigation_notes"]
        },
        "argument": {
            "title": "LEGAL ARGUMENTS",
            "sections": ["preamble", "facts", "legal_arguments", "conclusion"]
        },
        "memorandum": {
            "title": "MEMORANDUM OF UNDERSTANDING",
            "sections": ["preamble", "parties", "terms", "obligations", "signatures"]
        }
    }
    
    def __init__(self):
        # Import data_loader to access real precedent cases
        try:
            from app.services.data_loader import data_loader
            self.data_loader = data_loader
            logger.info(f"Drafting service connected to data_loader with {len(data_loader.precedent_cases or [])} precedent cases")
        except Exception as e:
            logger.warning(f"Could not load data_loader: {e}")
            self.data_loader = None
    
    async def generate_document(self, case_facts: str, doc_type: str) -> Dict[str, Any]:
        """
        Generate legal document with real citations from precedent database
        
        Args:
            case_facts: Facts of the case
            doc_type: Document type (petition, bail, fir, etc.)
            
        Returns:
            Generated document with citations
        """
        try:
            template = self.TEMPLATES.get(doc_type, self.TEMPLATES["petition"])
            
            # Get relevant citations from real precedent data
            citations = self._get_relevant_citations(case_facts, doc_type)
            
            # Generate content based on template + real citations
            content = self._generate_content(case_facts, doc_type, template, citations)
            
            # Calculate quality metrics based on actual citation matches
            quality_metrics = self._calculate_quality(content, citations, case_facts)
            
            return {
                "document_id": f"DOC-{doc_type}-{id(content)}",
                "content": content,
                "citations": citations,
                "quality_metrics": quality_metrics,
                "document_type": doc_type
            }
            
        except Exception as e:
            logger.error(f"Error generating document: {str(e)}")
            return {"error": str(e)}
    
    def _get_relevant_citations(self, case_facts: str, doc_type: str = "petition") -> List[Dict]:
        """Get relevant citations from real precedent database based on case facts"""
        citations = []
        
        if self.data_loader and self.data_loader.precedent_cases:
            # FIRST: Detect case type from facts to ensure correct domain matching
            case_type = self._guess_case_type(case_facts)
            logger.info(f"Detected case type: '{case_type}' for drafting citation search")
            
            # Extract key legal terms from facts (skip common words)
            stop_words = {
                "the", "and", "for", "was", "were", "has", "had", "have", "been",
                "with", "this", "that", "from", "are", "not", "but", "they", "she",
                "his", "her", "him", "who", "which", "when", "where", "how", "what",
                "about", "also", "been", "case", "filed", "court", "against", "under",
                "upon", "into", "over", "such", "than", "other", "shall", "will",
                "would", "could", "should", "being", "after", "before", "between",
                "through", "during", "while", "above", "below", "each", "every",
                "some", "any", "most", "then", "just", "only", "very", "year",
                "date", "time", "fact", "facts", "matter", "regard", "state",
            }
            facts_words = case_facts.lower().split()
            key_terms = [w for w in facts_words if len(w) > 3 and w not in stop_words]
            # Build a focused search query from key terms (max 12 words)
            search_query = " ".join(key_terms[:12])
            
            if not search_query:
                search_query = case_facts[:200]
            
            # Search with case type filter for accurate results
            found = self.data_loader.search_precedent_cases(
                query=search_query,
                case_type=case_type if case_type else None,
                limit=10
            )
            
            if found:
                for idx, case in enumerate(found):
                    relevance = "High" if case.get("relevance_score", 0) > 40 else \
                                "Medium" if case.get("relevance_score", 0) > 20 else "Low"
                    
                    court_abbr = self._court_abbreviation(case.get("court", ""))
                    year = case.get("year", "")
                    citation_str = f"({year}) {court_abbr} {case.get('id', '')}"
                    
                    citations.append({
                        "case_name": case.get("case_name", "Unknown"),
                        "year": year,
                        "citation": citation_str,
                        "relevance": relevance,
                        "court": case.get("court", ""),
                        "state": case.get("state", ""),
                        "case_type": case.get("case_type", ""),
                        "sections": case.get("sections", []),
                        "key_issues": case.get("key_issues", []),
                        "summary": case.get("summary", ""),
                        "outcome": case.get("outcome", ""),
                        "precedent_strength": case.get("precedent_strength", 0),
                        "paragraphs": self._assign_paragraphs(idx, len(found))
                    })
            
            # If not enough results, try broader search but still within same case type
            if len(citations) < 5 and case_type:
                extra = self.data_loader.search_precedent_cases(
                    query=case_type.lower(),
                    case_type=case_type,
                    limit=8
                )
                existing_ids = {c.get("citation") for c in citations}
                for case in extra:
                    court_abbr = self._court_abbreviation(case.get("court", ""))
                    year = case.get("year", "")
                    citation_str = f"({year}) {court_abbr} {case.get('id', '')}"
                    
                    if citation_str not in existing_ids:
                        citations.append({
                            "case_name": case.get("case_name", "Unknown"),
                            "year": year,
                            "citation": citation_str,
                            "relevance": "Medium",
                            "court": case.get("court", ""),
                            "state": case.get("state", ""),
                            "case_type": case.get("case_type", ""),
                            "sections": case.get("sections", []),
                            "key_issues": case.get("key_issues", []),
                            "summary": case.get("summary", ""),
                            "outcome": case.get("outcome", ""),
                            "precedent_strength": case.get("precedent_strength", 0),
                            "paragraphs": self._assign_paragraphs(len(citations), 10)
                        })
                        if len(citations) >= 10:
                            break
        
        # Sort by relevance then strength
        relevance_order = {"High": 3, "Medium": 2, "Low": 1}
        citations.sort(key=lambda c: (
            relevance_order.get(c.get("relevance", "Low"), 0),
            c.get("precedent_strength", 0)
        ), reverse=True)
        
        return citations[:10]
    
    def _court_abbreviation(self, court: str) -> str:
        """Get court abbreviation for citation"""
        court_lower = court.lower()
        if "supreme" in court_lower:
            return "SCC"
        elif "high" in court_lower:
            return "HC"
        elif "district" in court_lower:
            return "DC"
        elif "tribunal" in court_lower:
            return "Trib."
        return court[:3].upper() if court else "Ct."
    
    def _guess_case_type(self, case_facts: str) -> str:
        """Guess the case type from case facts text"""
        facts_lower = case_facts.lower()
        type_keywords = {
            "Criminal": ["murder", "rape", "sexual", "molestation", "pocso", "assault", "theft",
                        "robbery", "kidnapping", "abduction", "dacoity", "rioting", "dowry",
                        "fir", "accused", "bail", "arrest", "criminal", "police", "ipc", "crpc",
                        "offense", "crime", "complaint", "homicide", "extortion", "forgery",
                        "domestic violence", "stalking", "acid attack", "narcotics", "ndps",
                        "drugs", "culpable", "grievous", "hurt", "victim", "prosecution"],
            "Civil": ["contract", "breach", "damages", "negligence", "civil", "suit", "decree", 
                      "injunction", "plaintiff", "defendant", "tort", "compensation"],
            "Property": ["property", "land", "title", "possession", "eviction", "tenant", "landlord",
                        "lease", "encroachment", "ownership", "boundary"],
            "Family": ["divorce", "custody", "marriage", "maintenance", "alimony", "family", "child",
                      "husband", "wife", "domestic", "matrimonial", "guardianship"],
            "Commercial": ["company", "corporate", "business", "commercial", "trademark", "patent",
                          "insolvency", "bankruptcy", "arbitration"],
            "Tax": ["tax", "income", "gst", "assessment", "revenue", "tribunal", "taxation"],
            "Constitutional": ["fundamental", "rights", "constitution", "article", "writ", "petition",
                              "habeas corpus", "mandamus"],
            "Labour": ["employment", "worker", "labour", "wages", "termination", "industrial"],
        }
        
        scores = {}
        for case_type, keywords in type_keywords.items():
            score = sum(1 for kw in keywords if kw in facts_lower)
            if score > 0:
                scores[case_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return ""
    
    def _assign_paragraphs(self, idx: int, total: int) -> List[int]:
        """Assign paragraph references based on position"""
        # Simulate which paragraphs in the document cite this case
        base = (idx * 3) + 2
        return [base, base + 3, base + 6] if idx < 3 else [base, base + 2]
    
    def _generate_content(self, case_facts: str, doc_type: str, template: Dict, citations: List[Dict]) -> str:
        """Generate document content with real citations embedded"""
        title = template.get('title', 'LEGAL DOCUMENT')
        
        content = f"{'='*60}\n"
        content += f"{title}\n"
        content += f"{'='*60}\n\n"
        
        content += "IN THE MATTER OF:\n"
        content += "The Applicant/Petitioner\nvs.\nThe Respondent/State\n\n"
        content += f"{'─'*60}\n\n"
        
        # PREAMBLE
        content += "PREAMBLE\n\n"
        if doc_type == "petition":
            content += "The instant petition is filed seeking relief under the applicable provisions of law.\n\n"
        elif doc_type == "bail":
            content += "The present application is filed seeking grant of bail for the applicant.\n\n"
        elif doc_type == "fir":
            content += "The following information is provided for registration of a First Information Report.\n\n"
        elif doc_type == "argument":
            content += "The following legal arguments are submitted for the consideration of the Hon'ble Court.\n\n"
        else:
            content += "This document is prepared for the purposes outlined herein.\n\n"
        
        # FACTS OF THE CASE
        content += f"{'─'*60}\n"
        content += "FACTS OF THE CASE\n\n"
        content += f"{case_facts}\n\n"
        
        # APPLICABLE LEGAL PROVISIONS
        all_sections = set()
        for c in citations:
            for s in c.get("sections", []):
                all_sections.add(s)
        
        if all_sections:
            content += f"{'─'*60}\n"
            content += "APPLICABLE LEGAL PROVISIONS\n\n"
            for i, section in enumerate(list(all_sections)[:12], 1):
                content += f"  {i}. {section}\n"
            content += "\n"
        
        # SUPPORTING PRECEDENTS
        if citations:
            content += f"{'─'*60}\n"
            content += "SUPPORTING PRECEDENTS & CITED CASES\n\n"
            content += "The following judicial precedents are relied upon in support of this case:\n\n"
            
            for i, c in enumerate(citations, 1):
                content += f"  {i}. {c['case_name']} ({c['year']})\n"
                content += f"     Citation: {c['citation']}\n"
                content += f"     Court: {c.get('court', 'N/A')} | State: {c.get('state', 'N/A')}\n"
                content += f"     Relevance: {c['relevance']}\n"
                if c.get("summary"):
                    content += f"     Summary: {c['summary'][:150]}...\n"
                if c.get("outcome"):
                    content += f"     Outcome: {c['outcome']}\n"
                if c.get("key_issues"):
                    content += f"     Key Issues: {', '.join(c['key_issues'])}\n"
                content += "\n"
        
        # LEGAL ARGUMENTS
        content += f"{'─'*60}\n"
        content += "LEGAL ARGUMENTS\n\n"
        
        if doc_type == "petition":
            content += "A. ABUSE OF PROCESS / GROUNDS FOR RELIEF\n\n"
            if citations:
                top = citations[0]
                content += f"   As established in {top['case_name']} ({top['year']}), "
                content += f"the Hon'ble {top.get('court', 'Court')} held that "
                if top.get("outcome"):
                    content += f"the outcome was: {top['outcome']}.\n"
                else:
                    content += "relief should be granted where applicable grounds are made out.\n"
                content += f"   This precedent is directly applicable to the present matter.\n\n"
            
            content += "B. LEGAL PROVISIONS IN SUPPORT\n\n"
            if all_sections:
                for section in list(all_sections)[:5]:
                    content += f"   • {section} — Applicable to the facts of this case\n"
                content += "\n"
            
            content += "C. PRAYER FOR RELIEF\n\n"
            content += "   The petitioner submits that on the basis of the above precedents\n"
            content += "   and applicable legal provisions, the relief sought is just and equitable.\n\n"
        
        elif doc_type == "bail":
            content += "A. GROUNDS FOR BAIL\n\n"
            content += "   The applicant is entitled to bail on the following grounds:\n"
            content += "   • No prior criminal record\n"
            content += "   • Cooperative with investigation\n"
            content += "   • Willingness to comply with conditions\n\n"
            
            if citations:
                content += "B. SUPPORTING CASE LAW\n\n"
                for c in citations[:5]:
                    content += f"   • In {c['case_name']} ({c['year']}), the {c.get('court', 'Court')} "
                    content += f"addressed issues of {', '.join(c.get('key_issues', ['bail']))}\n"
                content += "\n"
        
        else:
            content += "   Based on the applicable legal provisions and cited precedents,\n"
            content += "   the present case is supported by established judicial principles.\n\n"
            if citations:
                for c in citations[:5]:
                    content += f"   • {c['case_name']} ({c['year']}) — {c.get('outcome', 'Decided')}\n"
                content += "\n"
        
        # RELIEF SOUGHT
        content += f"{'─'*60}\n"
        content += "RELIEF SOUGHT\n\n"
        content += "  1. The instant application/petition be allowed\n"
        content += "  2. Appropriate relief as prayed for be granted\n"
        content += "  3. Any other relief the Hon'ble Court may deem fit\n\n"
        
        # SIGNATURE
        content += f"{'─'*60}\n"
        content += f"\n                                    Dated: {datetime.now().strftime('%d/%m/%Y')}\n\n"
        content += "                                    Signed by: _____________\n"
        content += "                                    Counsel for the Petitioner/Applicant\n"
        content += f"\n{'='*60}\n"
        content += "Generated by Nyay AI\n"
        content += f"Total Precedents Cited: {len(citations)}\n"
        content += f"{'='*60}\n"
        
        return content
    
    def _calculate_quality(self, content: str, citations: List[Dict], case_facts: str) -> Dict[str, float]:
        """Calculate document quality metrics based on actual data"""
        # Citation strength: based on how many and how relevant
        high_count = sum(1 for c in citations if c.get("relevance") == "High")
        med_count = sum(1 for c in citations if c.get("relevance") == "Medium")
        total = len(citations)
        
        citation_strength = min(1.0, (high_count * 0.15 + med_count * 0.08 + total * 0.03))
        
        # Legal alignment: based on section coverage
        section_count = len(set(s for c in citations for s in c.get("sections", [])))
        legal_alignment = min(1.0, section_count * 0.08 + 0.3)
        
        # Completeness: based on content length and section coverage
        completeness = min(1.0, len(content) / 2000 * 0.6 + (0.4 if total >= 3 else total * 0.13))
        
        overall = (citation_strength + legal_alignment + completeness) / 3
        
        return {
            "citation_strength": round(citation_strength, 2),
            "legal_alignment": round(legal_alignment, 2),
            "completeness": round(completeness, 2),
            "overall_score": round(overall, 2)
        }
    
    async def generate_pdf(self, case_facts: str, doc_type: str, document_content: str = None) -> Dict[str, Any]:
        """
        Generate PDF version of legal document
        
        Args:
            case_facts: Facts of the case
            doc_type: Document type
            document_content: Pre-generated document content (optional)
            
        Returns:
            Dict with PDF content (base64 encoded) or error
        """
        try:
            if not HAS_REPORTLAB:
                return {
                    "error": "PDF generation not available. Install reportlab: pip install reportlab",
                    "status": "error"
                }
            
            # Generate document if not provided
            if not document_content:
                doc_result = await self.generate_document(case_facts, doc_type)
                if "error" in doc_result:
                    return doc_result
                document_content = doc_result.get("content", "")
                citations = doc_result.get("citations", [])
            else:
                citations = self._get_relevant_citations(case_facts, doc_type)
            
            # Create PDF
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=1*inch,
                bottomMargin=1*inch,
                title=f"Legal Document - {doc_type}",
                author="Nyay AI"
            )
            
            # Build PDF content
            story = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1a3a52'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceAfter=12,
                lineHeight=14
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=13,
                textColor=colors.HexColor('#2c5aa0'),
                spaceAfter=10,
                spaceBefore=10,
                fontName='Helvetica-Bold'
            )
            
            # Add content to PDF
            template = self.TEMPLATES.get(doc_type, self.TEMPLATES["petition"])
            
            # Title
            title_text = template.get('title', 'LEGAL DOCUMENT')
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Metadata
            now = datetime.now()
            metadata_style = ParagraphStyle(
                'Metadata',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                spaceAfter=10
            )
            story.append(Paragraph(f"Generated: {now.strftime('%B %d, %Y at %I:%M %p')}", metadata_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Case Facts Section
            story.append(Paragraph("CASE FACTS", heading_style))
            story.append(Paragraph(case_facts[:500], normal_style))
            story.append(Spacer(1, 0.15*inch))
            
            # Legal Grounds Section
            story.append(Paragraph("LEGAL GROUNDS & APPLICABLE SECTIONS", heading_style))
            
            # Use real sections from citations
            all_sections = set()
            for c in citations:
                for s in c.get("sections", []):
                    all_sections.add(s)
            
            if all_sections:
                for section in list(all_sections)[:8]:
                    story.append(Paragraph(f"• {section}", normal_style))
            else:
                story.append(Paragraph("• Applicable legal sections identified based on case facts", normal_style))
            
            story.append(Spacer(1, 0.15*inch))
            
            # Citation Section with real cases
            if citations:
                story.append(Paragraph("RELEVANT CITATIONS & PRECEDENTS", heading_style))
                
                # Create citations table
                citation_data = [["Case Name", "Year", "Court", "Citation", "Relevance"]]
                for citation in citations[:8]:  # Up to 8 citations in PDF
                    citation_data.append([
                        citation.get("case_name", "")[:35],
                        str(citation.get("year", "")),
                        citation.get("court", "")[:15],
                        citation.get("citation", "")[:20],
                        citation.get("relevance", "")
                    ])
                
                citation_table = Table(citation_data, colWidths=[2*inch, 0.6*inch, 1*inch, 1.2*inch, 0.7*inch])
                citation_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
                ]))
                
                story.append(citation_table)
                story.append(Spacer(1, 0.15*inch))
            
            # Relief Sought Section
            story.append(Paragraph("RELIEF SOUGHT", heading_style))
            relief_text = "Primary Relief: As per law and justice<br/>Alternative Relief: As may be deemed fit by the Honorable Court"
            story.append(Paragraph(relief_text, normal_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Footer
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
            story.append(Paragraph(
                f"Generated by Nyay AI | {len(citations)} precedents cited | "
                f"Document type: {doc_type}",
                footer_style
            ))
            
            # Build PDF
            doc.build(story)
            
            # Convert to base64 for response
            pdf_content = pdf_buffer.getvalue()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            return {
                "status": "success",
                "document_type": doc_type,
                "file_name": f"legal_document_{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "pdf_base64": pdf_base64,
                "pdf_size_bytes": len(pdf_content),
                "message": f"PDF generated with {len(citations)} real precedent citations"
            }
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return {
                "error": str(e),
                "status": "error"
            }
