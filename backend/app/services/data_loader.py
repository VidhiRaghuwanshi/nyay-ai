"""Data loader service for loading real datasets"""
import pandas as pd
import json
import os
from typing import List, Dict, Optional
from pathlib import Path

class DataLoaderService:
    """Load and manage real data from CSV and JSON files"""
    
    def __init__(self):
        self.datasets_path = Path(__file__).parent.parent.parent.parent / "datasets"
        self.judicial_data = None
        self.court_backlog_data = None
        self.judgment_data = None
        self.case_precedents = None
        self.precedent_cases = None  # From JSON
        self.precedent_index = {}    # Quick lookup by ID
        self.dataset_metadata = {}
        self._load_data()
    
    def _load_data(self):
        """Load all datasets on initialization"""
        self.load_judicial_delay_data()
        self.load_court_backlog_data()
        self.load_judgment_data()
        self._generate_precedent_cases()
        self.load_precedent_json()
    
    def load_judicial_delay_data(self) -> Optional[pd.DataFrame]:
        """Load judicial delay dataset"""
        try:
            file_path = self.datasets_path / "judicial_delay_dataset.csv"
            if file_path.exists():
                self.judicial_data = pd.read_csv(file_path)
                self._record_dataset(file_path.name, len(self.judicial_data), list(self.judicial_data.columns))
                return self.judicial_data
            return None
        except Exception as e:
            print(f"Error loading judicial data: {e}")
            return None

    def load_court_backlog_data(self) -> Optional[pd.DataFrame]:
        """Load NDAP high-court backlog data when available."""
        file_path = self.datasets_path / "NDAP_REPORT_7149.csv"
        try:
            if not file_path.exists():
                return None
            frame = pd.read_csv(file_path)
            numeric_columns = [
                column for column in frame.columns
                if column.startswith("Cases pending")
                or column.startswith("Pending cases")
                or column.startswith("Cases that were")
                or column.startswith("Writ petition")
                or column.startswith("Second appeal")
                or column.startswith("First appeal")
                or column.startswith("Appeal cases")
                or column.startswith("Petition cases")
                or column.startswith("Revision cases")
                or column.startswith("Reference cases")
                or column.startswith("Suit cases")
                or column.startswith("Review cases")
                or column.startswith("Application cases")
            ]
            for column in numeric_columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
            self.court_backlog_data = frame
            self._record_dataset(file_path.name, len(frame), list(frame.columns))
            return frame
        except Exception as error:
            print(f"Error loading court backlog data: {error}")
            return None

    def load_judgment_data(self) -> Optional[pd.DataFrame]:
        """Load Supreme Court judgment metadata for citation-aware search."""
        file_path = self.datasets_path / "judgments.csv"
        try:
            if not file_path.exists():
                return None
            frame = pd.read_csv(file_path, dtype=str).fillna("")
            frame["judgment_dates"] = pd.to_datetime(
                frame["judgment_dates"], dayfirst=True, errors="coerce"
            )
            self.judgment_data = frame
            self._record_dataset(file_path.name, len(frame), list(frame.columns))
            return frame
        except Exception as error:
            print(f"Error loading judgment data: {error}")
            return None

    def _record_dataset(self, name: str, rows: int, columns: List[str]) -> None:
        self.dataset_metadata[name] = {
            "name": name,
            "rows": rows,
            "columns": columns,
            "path": str(self.datasets_path / name),
        }
    
    def load_precedent_json(self) -> Optional[List[Dict]]:
        """Load precedent cases from JSON file"""
        try:
            file_path = self.datasets_path / "precedent_cases.json"
            if not file_path.exists():
                # Try alternate name
                file_path = self.datasets_path / "indian_legal_cases_2000.json"
            
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self.precedent_cases = json.load(f)
                
                # Build index for quick lookup
                self.precedent_index = {}
                for case in self.precedent_cases:
                    self.precedent_index[case["id"]] = case
                
                print(f"Loaded {len(self.precedent_cases)} precedent cases from JSON")
                return self.precedent_cases
            else:
                print("No precedent JSON file found")
                self.precedent_cases = []
                return []
        except Exception as e:
            print(f"Error loading precedent JSON: {e}")
            self.precedent_cases = []
            return []
    
    def search_precedent_cases(self, query: str, case_type: str = None,
                                court: str = None, limit: int = 20) -> List[Dict]:
        """Full-text search across precedent cases with case-type awareness"""
        if not self.precedent_cases:
            return []
        
        results = []
        query_lower = query.lower().strip()
        query_words = [w for w in query_lower.split() if len(w) > 2]
        
        # Detect the dominant legal domain from the query to filter irrelevant results
        domain_keywords = {
            "Criminal": {"murder", "rape", "assault", "robbery", "theft", "kidnapping", "fir",
                         "accused", "bail", "arrest", "criminal", "police", "ipc", "crpc",
                         "offense", "crime", "homicide", "abduction", "dacoity", "rioting",
                         "dowry", "molestation", "pocso", "ndps", "drugs", "narcotics",
                         "extortion", "forgery", "cheating", "fraud"},
            "Civil": {"contract", "breach", "damages", "negligence", "civil", "suit", "decree",
                      "injunction", "plaintiff", "defendant", "tort", "compensation"},
            "Property": {"property", "land", "title", "possession", "eviction", "tenant",
                         "landlord", "lease", "encroachment", "ownership", "boundary"},
            "Family": {"divorce", "custody", "marriage", "maintenance", "alimony", "family",
                       "child", "husband", "wife", "domestic", "matrimonial", "guardianship"},
            "Tax": {"tax", "income tax", "gst", "assessment", "revenue", "tribunal", "taxation"},
            "Commercial": {"company", "corporate", "business", "trademark", "patent",
                           "insolvency", "bankruptcy", "arbitration", "partnership"},
            "Constitutional": {"fundamental", "constitution", "article", "writ", "petition",
                               "habeas corpus", "mandamus"},
            "Labour": {"employment", "worker", "labour", "wages", "termination", "industrial"},
        }
        
        # Detect query domain
        query_domain = None
        if case_type:
            query_domain = case_type
        else:
            domain_scores = {}
            for domain, kws in domain_keywords.items():
                hits = sum(1 for w in query_words if w in kws)
                if query_lower in kws:
                    hits += 3
                if hits > 0:
                    domain_scores[domain] = hits
            if domain_scores:
                query_domain = max(domain_scores, key=domain_scores.get)
        
        for case in self.precedent_cases:
            score = 0
            
            # Case name match
            name = case.get("case_name", "").lower()
            if query_lower in name:
                score += 50
            else:
                for word in query_words:
                    if word in name:
                        score += 15
            
            # Summary match
            summary = case.get("summary", "").lower()
            for word in query_words:
                if word in summary:
                    score += 10
            
            # Sections match
            for section in case.get("sections", []):
                sec_lower = section.lower()
                if query_lower in sec_lower:
                    score += 40
                for word in query_words:
                    if word in sec_lower:
                        score += 15
            
            # Key issues match
            for issue in case.get("key_issues", []):
                issue_lower = issue.lower()
                if query_lower in issue_lower:
                    score += 35
                for word in query_words:
                    if word in issue_lower:
                        score += 12
            
            # Relevance tags match
            for tag in case.get("relevance_tags", []):
                tag_lower = tag.lower()
                if query_lower in tag_lower:
                    score += 30
                for word in query_words:
                    if word in tag_lower:
                        score += 10
            
            # CASE TYPE ENFORCEMENT: heavily penalize wrong case types
            case_case_type = case.get("case_type", "").strip()
            if query_domain:
                if case_case_type.lower() == query_domain.lower():
                    score += 25  # Boost matching case type
                else:
                    # Heavily penalize wrong case type - multiply by 0.1
                    score = int(score * 0.1)
            
            # Explicit case_type filter
            if case_type:
                if case_case_type.lower() != case_type.lower():
                    score = int(score * 0.05)
            
            # Court filter boost
            if court:
                if court.lower() in case.get("court", "").lower():
                    score += 10
            
            if score <= 0:
                continue
            
            results.append({
                **case,
                "relevance_score": min(100, score),
            })
        
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]

    def search_judgments(self, query: str, limit: int = 20) -> List[Dict]:
        """Search judgment metadata using party names, advocates, bench and case number."""
        if self.judgment_data is None or not query.strip():
            return []
        query_terms = [term for term in query.lower().split() if len(term) > 1]
        searchable_columns = [
            "case_no", "pet", "res", "pet_adv", "res_adv",
            "bench", "judgement_by", "diary_no",
        ]
        results = []
        for _, row in self.judgment_data.iterrows():
            haystack = " ".join(str(row.get(column, "")) for column in searchable_columns).lower()
            score = sum(1 for term in query_terms if term in haystack)
            if score == 0:
                continue
            results.append({
                "id": f"SC-{row.get('diary_no', '')}",
                "diary_no": row.get("diary_no", ""),
                "case_no": row.get("case_no", ""),
                "petitioner": row.get("pet", ""),
                "respondent": row.get("res", ""),
                "bench": row.get("bench", ""),
                "judgment_by": row.get("judgement_by", ""),
                "judgment_date": (
                    row["judgment_dates"].date().isoformat()
                    if not pd.isna(row["judgment_dates"]) else None
                ),
                "source_path": row.get("temp_link", ""),
                "relevance_score": score,
            })
        results.sort(key=lambda item: item["relevance_score"], reverse=True)
        return results[:limit]

    def get_dataset_catalog(self) -> Dict[str, Dict]:
        """Return safe metadata for all datasets loaded by Nyay AI."""
        catalog = dict(self.dataset_metadata)
        if self.judicial_data is not None and "judicial_delay_dataset.csv" not in catalog:
            self._record_dataset(
                "judicial_delay_dataset.csv",
                len(self.judicial_data),
                list(self.judicial_data.columns),
            )
        if self.precedent_cases is not None and "precedent_cases.json" not in catalog:
            self._record_dataset(
                "precedent_cases.json",
                len(self.precedent_cases),
                list(self.precedent_cases[0].keys()) if self.precedent_cases else [],
            )
        return dict(self.dataset_metadata)
    
    def get_precedent_by_id(self, case_id: str) -> Optional[Dict]:
        """Get a specific precedent case by ID"""
        return self.precedent_index.get(case_id)
    
    def get_citation_graph(self, case_id: str, depth: int = 2) -> Dict:
        """Build citation graph for a case"""
        if not self.precedent_index:
            return {"nodes": [], "edges": []}
        
        case = self.precedent_index.get(case_id)
        if not case:
            return {"nodes": [], "edges": []}
        
        visited = set()
        nodes = []
        edges = []
        
        def traverse(cid, current_depth):
            if cid in visited or current_depth > depth:
                return
            visited.add(cid)
            
            c = self.precedent_index.get(cid)
            if not c:
                return
            
            nodes.append({
                "id": c["id"],
                "label": c["case_name"],
                "type": "case",
                "citations": c.get("citations", 0),
                "court": c.get("court", ""),
                "year": c.get("year", 0),
                "case_type": c.get("case_type", ""),
                "outcome": c.get("outcome", ""),
                "precedent_strength": c.get("precedent_strength", 0),
            })
            
            # Add edges from cites
            for cited_id in c.get("cites", []):
                if cited_id in self.precedent_index:
                    edges.append({
                        "source": cid,
                        "target": cited_id,
                        "relation": "cites",
                    })
                    traverse(cited_id, current_depth + 1)
            
            # Add edges from cited_by
            for citing_id in c.get("cited_by", []):
                if citing_id in self.precedent_index:
                    edges.append({
                        "source": citing_id,
                        "target": cid,
                        "relation": "cited_by",
                    })
                    traverse(citing_id, current_depth + 1)
        
        traverse(case_id, 0)
        
        # Also add section nodes for the root case
        for section in case.get("sections", []):
            nodes.append({
                "id": f"sec_{section.replace(' ', '_')}",
                "label": section,
                "type": "section",
                "citations": 0,
            })
            edges.append({
                "source": case_id,
                "target": f"sec_{section.replace(' ', '_')}",
                "relation": "applies",
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_precedent_stats(self) -> Dict:
        """Get statistics from precedent cases"""
        if not self.precedent_cases:
            return {"total": 0}
        
        types = {}
        courts = {}
        states = {}
        years = {}
        
        for c in self.precedent_cases:
            ct = c.get("case_type", "Unknown")
            types[ct] = types.get(ct, 0) + 1
            court = c.get("court", "Unknown")
            courts[court] = courts.get(court, 0) + 1
            state = c.get("state", "Unknown")
            states[state] = states.get(state, 0) + 1
            year = c.get("year", 0)
            years[year] = years.get(year, 0) + 1
        
        return {
            "total": len(self.precedent_cases),
            "by_type": types,
            "by_court": courts,
            "by_state": states,
            "by_year": dict(sorted(years.items())),
        }
    
    def _generate_precedent_cases(self):
        """Generate precedent cases from judicial data"""
        if self.judicial_data is None:
            self.case_precedents = []
            return
        
        cases = []
        for idx, row in self.judicial_data.iterrows():
            case = {
                "id": f"CASE_{idx+1001}",
                "case_type": row.get("case_type", "Unknown"),
                "state": row.get("state", "Unknown"),
                "court_level": row.get("court_level", "District"),
                "filing_year": int(row.get("filing_year", 2020)),
                "number_of_hearings": int(row.get("number_of_hearings", 0)),
                "judge_workload": int(row.get("judge_workload", 400)),
                "historical_disposal_rate": float(row.get("historical_disposal_rate", 0.5)),
                "delay_months": float(row.get("delay_months", 30)),
                "status": "Closed" if row.get("delay_months", 0) > 0 else "Pending",
                "case_summary": self._generate_case_summary(row),
                "key_issues": self._generate_key_issues(row),
                "outcome": self._generate_outcome(row),
                "cited_sections": self._generate_sections(row),
            }
            cases.append(case)
        
        self.case_precedents = cases
    
    def _generate_case_summary(self, row) -> str:
        case_type = row.get("case_type", "Case")
        state = row.get("state", "")
        court = row.get("court_level", "Court")
        year = row.get("filing_year", 2020)
        summaries = {
            "Criminal": f"Criminal case filed in {state} {court} Court in {year}. Involved {row.get('number_of_hearings', 0)} hearings.",
            "Civil": f"Civil dispute case filed in {state} {court} Court in {year}. Judge workload: {row.get('judge_workload', 400)} cases.",
            "Family": f"Family law case handled in {state} {court} Court. Disposal rate: {row.get('historical_disposal_rate', 0.5)*100}%.",
            "Commercial": f"Commercial litigation in {state} {court} Court. Case resolved with {row.get('delay_months', 30)} months delay.",
            "Property": f"Property dispute case in {state}. Court level: {court}. {row.get('number_of_hearings', 0)} hearings.",
        }
        return summaries.get(case_type, f"{case_type} case filed in {state} {court} Court in {year}")
    
    def _generate_key_issues(self, row) -> List[str]:
        case_type = row.get("case_type", "")
        issues_map = {
            "Criminal": ["Guilt/Innocence", "Evidence validity", "Due process", "Sentencing"],
            "Civil": ["Liability", "Damages", "Contract breach", "Negligence"],
            "Family": ["Custody", "Property division", "Support", "Divorce"],
            "Commercial": ["Breach of contract", "Business liability", "Financial disputes", "Corporate law"],
            "Property": ["Ownership rights", "Boundary dispute", "Title validity", "Land rights"],
        }
        return issues_map.get(case_type, ["Legal validity", "Jurisdiction", "Evidence"])
    
    def _generate_outcome(self, row) -> str:
        if row.get("historical_disposal_rate", 0) > 0.7:
            return "Resolved in favor of plaintiff"
        elif row.get("historical_disposal_rate", 0) > 0.4:
            return "Partially resolved with settlement"
        else:
            return "Case dismissed due to insufficient evidence"
    
    def _generate_sections(self, row) -> List[str]:
        case_type = row.get("case_type", "")
        sections_map = {
            "Criminal": ["IPC 420", "IPC 376", "CrPC 200", "Evidence Act 1872"],
            "Civil": ["CPC 1908 Section 12", "Limitation Act 1963", "Indian Contract Act 1872"],
            "Family": ["Hindu Marriage Act 1955", "Maintenance and Welfare Act 1985", "Divorce Act 1969"],
            "Commercial": ["Companies Act 2013", "Competition Act 2002", "Contract Act 1872"],
            "Property": ["Transfer of Property Act 1882", "Indian Easement Act 1882", "Land Acquisition Act"],
        }
        return sections_map.get(case_type, ["Indian Penal Code", "Code of Criminal Procedure"])
    
    def get_similar_cases(self, case_type: str, state: Optional[str] = None, limit: int = 5) -> List[Dict]:
        if not self.case_precedents:
            return []
        similar = [c for c in self.case_precedents if c["case_type"].lower() == case_type.lower()]
        if state:
            similar = [c for c in similar if c["state"].lower() == state.lower()]
        return similar[:limit]
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        if not self.case_precedents:
            return None
        for case in self.case_precedents:
            if case["id"] == case_id:
                return case
        return None
    
    def get_all_cases(self) -> List[Dict]:
        return self.case_precedents or []
    
    def get_case_statistics(self) -> Dict:
        if self.judicial_data is None:
            return {}
        return {
            "total_cases": len(self.judicial_data),
            "average_delay_months": float(self.judicial_data["delay_months"].mean()),
            "average_hearings": int(self.judicial_data["number_of_hearings"].mean()),
            "case_types": self.judicial_data["case_type"].unique().tolist(),
            "states": self.judicial_data["state"].unique().tolist(),
            "avg_disposal_rate": float(self.judicial_data["historical_disposal_rate"].mean()),
            "loaded_datasets": self.get_dataset_catalog(),
        }

# Create singleton instance
data_loader = DataLoaderService()
