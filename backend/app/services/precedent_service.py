"""Precedent Graph Engine Service - Uses real precedent_cases.json"""
import logging
import io
import base64
import csv
from datetime import datetime
from typing import List, Dict, Any

from .data_loader import data_loader

# Try importing reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

logger = logging.getLogger(__name__)


class PrecedentGraphService:
    """Service for precedent graph analysis using real case data"""
    
    def __init__(self):
        self.data_loader = data_loader
    
    async def search_precedents(self, query: str, case_type: str = None) -> Dict[str, Any]:
        """
        Search for similar precedents from real JSON dataset
        """
        try:
            # Search real precedent cases
            results = self.data_loader.search_precedent_cases(
                query=query,
                case_type=case_type,
                limit=20
            )
            
            similar_cases = []
            for case in results:
                similar_cases.append({
                    "case_id": case["id"],
                    "name": case["case_name"],
                    "case_type": case["case_type"],
                    "court": case["court"],
                    "state": case["state"],
                    "year": case["year"],
                    "citations": case.get("citations", 0),
                    "sections": case.get("sections", []),
                    "key_issues": case.get("key_issues", []),
                    "summary": case.get("summary", ""),
                    "outcome": case.get("outcome", ""),
                    "judges": case.get("judges", []),
                    "precedent_strength": case.get("precedent_strength", 0),
                    "similarity": case.get("relevance_score", 0),
                    "precedent_score": case.get("precedent_strength", 0),
                    "relevance": "High" if case.get("relevance_score", 0) > 60 else "Medium" if case.get("relevance_score", 0) > 30 else "Low",
                })
            
            # Get stats
            stats = self.data_loader.get_precedent_stats()
            
            # Build graph from ALL search results
            graph = self._build_search_graph(results)
            
            return {
                "query": query,
                "case_type_filtered": case_type,
                "total_found": len(similar_cases),
                "total_in_dataset": stats.get("total", 0),
                "similar_cases": similar_cases,
                "graph": graph,
            }
            
        except Exception as e:
            logger.error(f"Error searching precedents: {str(e)}")
            return {"error": str(e), "similar_cases": [], "total_found": 0}
    
    def _build_search_graph(self, search_results: List[Dict]) -> Dict[str, Any]:
        """
        Build a graph from ALL search results, showing interconnections.
        Each search result becomes a node. Edges are drawn where cases
        cite each other or share common sections/issues.
        """
        if not search_results:
            return {"nodes": [], "edges": []}
        
        nodes = []
        edges = []
        result_ids = {case["id"] for case in search_results}
        
        # Add all search results as case nodes
        for case in search_results:
            nodes.append({
                "id": case["id"],
                "label": case["case_name"],
                "type": "case",
                "citations": case.get("citations", 0),
                "court": case.get("court", ""),
                "year": case.get("year", 0),
                "case_type": case.get("case_type", ""),
                "outcome": case.get("outcome", ""),
                "precedent_strength": case.get("precedent_strength", 0),
                "state": case.get("state", ""),
                "relevance_score": case.get("relevance_score", 0),
            })
            
            # Add edges for direct citations within search results
            for cited_id in case.get("cites", []):
                if cited_id in result_ids:
                    edges.append({
                        "source": case["id"],
                        "target": cited_id,
                        "relation": "cites",
                    })
            
            for citing_id in case.get("cited_by", []):
                if citing_id in result_ids:
                    edges.append({
                        "source": citing_id,
                        "target": case["id"],
                        "relation": "cited_by",
                    })
        
        # Collect shared sections across cases to create section nodes
        section_cases = {}  # section -> list of case_ids using it
        for case in search_results:
            for section in case.get("sections", []):
                sec_key = section.strip()
                if sec_key not in section_cases:
                    section_cases[sec_key] = []
                section_cases[sec_key].append(case["id"])
        
        # Only add section nodes that are shared by 2+ cases (meaningful connections)
        for section, case_ids in section_cases.items():
            if len(case_ids) >= 2:
                sec_id = f"sec_{section.replace(' ', '_').replace(',', '')}"
                nodes.append({
                    "id": sec_id,
                    "label": section,
                    "type": "section",
                    "citations": len(case_ids),
                })
                for cid in case_ids:
                    edges.append({
                        "source": cid,
                        "target": sec_id,
                        "relation": "applies",
                    })
        
        # Deduplicate edges
        seen_edges = set()
        unique_edges = []
        for edge in edges:
            key = (edge["source"], edge["target"], edge["relation"])
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": unique_edges,
            "metrics": {
                "total_nodes": len(nodes),
                "total_connections": len(unique_edges),
                "case_nodes": sum(1 for n in nodes if n["type"] == "case"),
                "section_nodes": sum(1 for n in nodes if n["type"] == "section"),
            }
        }
    
    async def build_graph(self, case_id: str) -> Dict[str, Any]:
        """Build precedent graph for a single case using real citation data"""
        try:
            case = self.data_loader.get_precedent_by_id(case_id)
            if not case:
                return {"error": "Case not found", "case_id": case_id}
            
            # Get citation graph from data loader
            graph = self.data_loader.get_citation_graph(case_id, depth=2)
            
            return {
                "case_id": case_id,
                "case_details": {
                    "case_name": case["case_name"],
                    "case_type": case["case_type"],
                    "court": case["court"],
                    "state": case["state"],
                    "year": case["year"],
                    "sections": case.get("sections", []),
                    "key_issues": case.get("key_issues", []),
                    "summary": case.get("summary", ""),
                    "outcome": case.get("outcome", ""),
                    "judges": case.get("judges", []),
                    "precedent_strength": case.get("precedent_strength", 0),
                },
                "nodes": graph["nodes"],
                "edges": graph["edges"],
                "metrics": {
                    "total_nodes": len(graph["nodes"]),
                    "total_connections": len(graph["edges"]),
                    "cited_count": len(case.get("cited_by", [])),
                    "cites_count": len(case.get("cites", [])),
                    "precedent_strength": case.get("precedent_strength", 0),
                }
            }
            
        except Exception as e:
            logger.error(f"Error building graph: {str(e)}")
            return {"error": str(e)}
    
    async def get_case_details(self, case_id: str) -> Dict[str, Any]:
        """Get detailed case information"""
        case = self.data_loader.get_precedent_by_id(case_id)
        if not case:
            return {"error": "Case not found"}
        return case
    
    async def export_cases_pdf(self, case_ids: List[str], query: str = "") -> Dict[str, Any]:
        """Export selected cases as a PDF report"""
        try:
            if not HAS_REPORTLAB:
                return {
                    "error": "PDF generation not available. Install reportlab: pip install reportlab",
                    "status": "error"
                }
            
            # Gather case data
            cases = []
            for cid in case_ids:
                case = self.data_loader.get_precedent_by_id(cid)
                if case:
                    cases.append(case)
            
            if not cases:
                return {"error": "No valid cases found", "status": "error"}
            
            # Create PDF
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                rightMargin=0.6 * inch,
                leftMargin=0.6 * inch,
                topMargin=0.8 * inch,
                bottomMargin=0.8 * inch,
                title="Precedent Cases Report",
                author="Nyay AI"
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'ReportTitle', parent=styles['Heading1'],
                fontSize=20, textColor=colors.HexColor('#1a3a52'),
                spaceAfter=20, alignment=TA_CENTER, fontName='Helvetica-Bold'
            )
            subtitle_style = ParagraphStyle(
                'ReportSubtitle', parent=styles['Normal'],
                fontSize=11, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=30
            )
            heading_style = ParagraphStyle(
                'CaseHeading', parent=styles['Heading2'],
                fontSize=14, textColor=colors.HexColor('#2c5aa0'),
                spaceAfter=8, spaceBefore=16, fontName='Helvetica-Bold'
            )
            label_style = ParagraphStyle(
                'Label', parent=styles['Normal'],
                fontSize=9, textColor=colors.HexColor('#666666'),
                spaceAfter=2, fontName='Helvetica-Bold'
            )
            normal_style = ParagraphStyle(
                'Body', parent=styles['Normal'],
                fontSize=10, spaceAfter=8, leading=14
            )
            
            # Title page
            story.append(Paragraph("PRECEDENT CASES REPORT", title_style))
            story.append(Paragraph(
                f"Generated by Nyay AI on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                subtitle_style
            ))
            if query:
                story.append(Paragraph(f"Search Query: \"{query}\"", subtitle_style))
            story.append(Paragraph(f"Total Cases: {len(cases)}", subtitle_style))
            story.append(Spacer(1, 0.3 * inch))
            
            # Summary table
            summary_data = [["#", "Case Name", "Court", "Year", "Type", "Outcome"]]
            for i, c in enumerate(cases, 1):
                summary_data.append([
                    str(i),
                    c.get("case_name", "")[:40],
                    c.get("court", "")[:15],
                    str(c.get("year", "")),
                    c.get("case_type", ""),
                    c.get("outcome", "")[:20],
                ])
            
            summary_table = Table(summary_data, colWidths=[0.3 * inch, 2.5 * inch, 1 * inch, 0.5 * inch, 0.7 * inch, 1.2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(summary_table)
            story.append(PageBreak())
            
            # Individual case details
            for i, case in enumerate(cases, 1):
                story.append(Paragraph(f"Case {i}: {case.get('case_name', 'Unknown')}", heading_style))
                
                # Metadata row
                meta_data = [[
                    f"Court: {case.get('court', 'N/A')}",
                    f"State: {case.get('state', 'N/A')}",
                    f"Year: {case.get('year', 'N/A')}",
                    f"Type: {case.get('case_type', 'N/A')}",
                ]]
                meta_table = Table(meta_data, colWidths=[1.6 * inch] * 4)
                meta_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f4f8')),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                ]))
                story.append(meta_table)
                story.append(Spacer(1, 6))
                
                # Outcome
                if case.get("outcome"):
                    story.append(Paragraph("OUTCOME", label_style))
                    story.append(Paragraph(case["outcome"], normal_style))
                
                # Summary
                if case.get("summary"):
                    story.append(Paragraph("SUMMARY", label_style))
                    story.append(Paragraph(case["summary"], normal_style))
                
                # Sections
                if case.get("sections"):
                    story.append(Paragraph("LEGAL SECTIONS", label_style))
                    story.append(Paragraph(", ".join(case["sections"]), normal_style))
                
                # Key Issues
                if case.get("key_issues"):
                    story.append(Paragraph("KEY ISSUES", label_style))
                    story.append(Paragraph(", ".join(case["key_issues"]), normal_style))
                
                # Judges
                if case.get("judges"):
                    story.append(Paragraph("BENCH", label_style))
                    story.append(Paragraph(", ".join(case["judges"]), normal_style))
                
                # Citations info
                story.append(Paragraph("CITATION METRICS", label_style))
                story.append(Paragraph(
                    f"Total Citations: {case.get('citations', 0)} | "
                    f"Precedent Strength: {case.get('precedent_strength', 0)} | "
                    f"Cites: {len(case.get('cites', []))} cases | "
                    f"Cited By: {len(case.get('cited_by', []))} cases",
                    normal_style
                ))
                
                story.append(Spacer(1, 0.15 * inch))
                
                # Add separator between cases (except last)
                if i < len(cases):
                    story.append(Paragraph("─" * 80, ParagraphStyle(
                        'Sep', parent=styles['Normal'], fontSize=6,
                        textColor=colors.HexColor('#cccccc'), spaceAfter=8
                    )))
            
            # Footer
            story.append(Spacer(1, 0.3 * inch))
            footer_style = ParagraphStyle(
                'Footer', parent=styles['Normal'],
                fontSize=8, textColor=colors.grey, alignment=TA_CENTER
            )
            story.append(Paragraph(
                f"Generated by Nyay AI | {len(cases)} cases exported | "
                f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
                footer_style
            ))
            
            doc.build(story)
            pdf_content = pdf_buffer.getvalue()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            return {
                "status": "success",
                "file_name": f"precedent_cases_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "pdf_base64": pdf_base64,
                "pdf_size_bytes": len(pdf_content),
                "total_cases": len(cases),
                "message": f"PDF report generated with {len(cases)} cases"
            }
            
        except Exception as e:
            logger.error(f"Error exporting PDF: {str(e)}")
            return {"error": str(e), "status": "error"}
    
    async def export_cases_csv(self, case_ids: List[str]) -> Dict[str, Any]:
        """Export selected cases as CSV"""
        try:
            cases = []
            for cid in case_ids:
                case = self.data_loader.get_precedent_by_id(cid)
                if case:
                    cases.append(case)
            
            if not cases:
                return {"error": "No valid cases found", "status": "error"}
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "ID", "Case Name", "Case Type", "Court", "State", "Year",
                "Outcome", "Summary", "Sections", "Key Issues", "Judges",
                "Citations", "Precedent Strength"
            ])
            
            for c in cases:
                writer.writerow([
                    c.get("id", ""),
                    c.get("case_name", ""),
                    c.get("case_type", ""),
                    c.get("court", ""),
                    c.get("state", ""),
                    c.get("year", ""),
                    c.get("outcome", ""),
                    c.get("summary", ""),
                    "; ".join(c.get("sections", [])),
                    "; ".join(c.get("key_issues", [])),
                    "; ".join(c.get("judges", [])),
                    c.get("citations", 0),
                    c.get("precedent_strength", 0),
                ])
            
            csv_content = output.getvalue()
            csv_base64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            
            return {
                "status": "success",
                "file_name": f"precedent_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "csv_base64": csv_base64,
                "total_cases": len(cases),
                "message": f"CSV generated with {len(cases)} cases"
            }
        except Exception as e:
            logger.error(f"Error exporting CSV: {str(e)}")
            return {"error": str(e), "status": "error"}
