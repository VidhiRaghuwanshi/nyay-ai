import { useState } from 'react';
import { Network, Search, ZoomIn, ZoomOut, Loader2, Scale, MapPin, Calendar, Users, Download, FileText, FileSpreadsheet } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { precedentAPI } from '../services/api';

const CASE_TYPES = ['All', 'Criminal', 'Civil', 'Family', 'Commercial', 'Property', 'Constitutional', 'Tax', 'Labor'];

export default function PrecedentGraph() {
  const [searchQuery, setSearchQuery] = useState('');
  const [caseType, setCaseType] = useState('All');
  const [selectedCase, setSelectedCase] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const [graphData, setGraphData] = useState(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    setSelectedCase(null);
    setGraphData(null);
    try {
      const result = await precedentAPI.search(
        searchQuery,
        caseType === 'All' ? '' : caseType
      );
      setSearchResults(result);
      // Use graph from search results (built from ALL results)
      if (result.graph) {
        setGraphData(result.graph);
      }
    } catch (err) {
      console.error('Search failed:', err);
      setError('Search failed. Backend may be offline.');
    } finally {
      setLoading(false);
    }
  };

  const loadCaseGraph = async (caseId) => {
    try {
      const graph = await precedentAPI.analyze(caseId, caseType);
      if (graph && !graph.error) {
        setGraphData({ nodes: graph.nodes, edges: graph.edges, metrics: graph.metrics });
      }
    } catch { /* ignore */ }
  };

  // Download helpers
  const downloadBase64 = (base64, filename, mime) => {
    const byteChars = atob(base64);
    const byteNums = new Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) byteNums[i] = byteChars.charCodeAt(i);
    const blob = new Blob([new Uint8Array(byteNums)], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = async () => {
    if (!cases.length) return;
    setExporting(true);
    try {
      const ids = cases.map(c => c.case_id);
      const result = await precedentAPI.exportPDF(ids, searchQuery);
      if (result.pdf_base64) {
        downloadBase64(result.pdf_base64, result.file_name || 'cases.pdf', 'application/pdf');
      }
    } catch (err) { console.error('PDF export failed:', err); setError('PDF export failed.'); }
    finally { setExporting(false); }
  };

  const handleExportCSV = async () => {
    if (!cases.length) return;
    setExporting(true);
    try {
      const ids = cases.map(c => c.case_id);
      const result = await precedentAPI.exportCSV(ids);
      if (result.csv_base64) {
        downloadBase64(result.csv_base64, result.file_name || 'cases.csv', 'text/csv');
      }
    } catch (err) { console.error('CSV export failed:', err); setError('CSV export failed.'); }
    finally { setExporting(false); }
  };

  // Graph rendering
  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];
  const cases = searchResults?.similar_cases || [];

  // Improved layout: case nodes in concentric arcs, sections on outer ring
  const getNodePositions = () => {
    if (nodes.length === 0) return {};
    const positions = {};
    const centerX = 450, centerY = 260;
    const caseNodes = nodes.filter(n => n.type === 'case');
    const sectionNodes = nodes.filter(n => n.type === 'section');
    const degree = new Map();
    edges.forEach((edge) => {
      degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
      degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
    });
    const hash = (value) => Array.from(String(value)).reduce(
      (total, character) => ((total * 31) + character.charCodeAt(0)) % 1000003,
      7
    );
    const orderedCases = [...caseNodes].sort((a, b) => hash(a.id) - hash(b.id));
    const caseRadius = Math.min(215, 105 + orderedCases.length * 5 + (edges.length % 7) * 5);
    const secRadius = caseRadius + 55 + (sectionNodes.length % 4) * 10;

    orderedCases.forEach((node, i) => {
      if (caseNodes.length === 1) {
        positions[node.id] = [centerX, centerY];
      } else {
        const angle = (2 * Math.PI * i) / orderedCases.length - Math.PI / 2
          + ((hash(node.id) % 17) - 8) / 100;
        const nodeRadius = caseRadius + Math.min(35, (degree.get(node.id) || 0) * 4);
        positions[node.id] = [
          centerX + nodeRadius * Math.cos(angle),
          centerY + nodeRadius * Math.sin(angle),
        ];
      }
    });
    sectionNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / (sectionNodes.length || 1) - Math.PI / 4
        + ((hash(node.id) % 13) - 6) / 100;
      positions[node.id] = [
        centerX + secRadius * Math.cos(angle),
        centerY + secRadius * Math.sin(angle),
      ];
    });
    return positions;
  };
  const positions = getNodePositions();

  const getRelColor = (rel) => {
    if (rel === 'cites') return 'var(--legal-blue)';
    if (rel === 'cited_by') return 'var(--gold-deep)';
    if (rel === 'applies') return 'var(--status-ok)';
    return 'var(--ink-subtle)';
  };

  const svgW = 900, svgH = 520;

  return (
    <div className="animate-fade-in">
      <PageHeader
        icon={Network}
        title="Precedent Graph Engine"
        description={`Search ${searchResults?.total_in_dataset || '7,000'}+ real Indian legal cases and visualize citation networks`}
        accentColor="var(--legal-blue)"
      />

      {error && (
        <div style={{ padding: '10px 16px', background: 'var(--status-warn-bg)', border: '1px solid rgba(176,140,26,0.2)', borderRadius: 'var(--radius-md)', marginBottom: 16, fontSize: 13, color: 'var(--status-warn)' }}>
          {error}
        </div>
      )}

      {/* Search Bar */}
      <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block' }}>Search Cases</label>
            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--ink-subtle)' }} />
              <input
                type="text"
                placeholder="e.g. murder, IPC 302, bail, property dispute, divorce..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="input-ink"
                style={{ paddingLeft: 36 }}
              />
            </div>
          </div>
          <div style={{ width: 160 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block' }}>Case Type</label>
            <select className="select-ink" value={caseType} onChange={(e) => setCaseType(e.target.value)}>
              {CASE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <button className="btn-ink" onClick={handleSearch} disabled={loading} style={{ height: 42 }}>
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} Search
          </button>
        </div>
        {searchResults && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10, flexWrap: 'wrap', gap: 8 }}>
            <p style={{ fontSize: 12, color: 'var(--ink-faint)' }}>
              Found <strong style={{ color: 'var(--ink)' }}>{searchResults.total_found}</strong> matching cases
              {searchResults.total_in_dataset > 0 && ` out of ${searchResults.total_in_dataset.toLocaleString()} total`}
            </p>
            {cases.length > 0 && (
              <div style={{ display: 'flex', gap: 6 }}>
                <button onClick={handleExportPDF} disabled={exporting} className="btn-ghost" style={{ fontSize: 11, padding: '5px 12px', display: 'flex', alignItems: 'center', gap: 4 }}>
                  {exporting ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />} Download PDF
                </button>
                <button onClick={handleExportCSV} disabled={exporting} className="btn-ghost" style={{ fontSize: 11, padding: '5px 12px', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <FileSpreadsheet size={12} /> Download CSV
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="page-grid-wide">
        {/* Left */}
        <div>
          {/* Graph Visualization */}
          {nodes.length > 0 && (
            <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>
                  Citation Graph
                  <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--ink-faint)', marginLeft: 8 }}>
                    {nodes.length} nodes · {edges.length} links · “{searchResults?.query}”
                  </span>
                </h2>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button onClick={() => setZoom(Math.min(zoom + 0.15, 2.5))} className="btn-ghost" style={{ padding: '6px 8px' }}><ZoomIn size={16} /></button>
                  <button onClick={() => setZoom(Math.max(zoom - 0.15, 0.3))} className="btn-ghost" style={{ padding: '6px 8px' }}><ZoomOut size={16} /></button>
                </div>
              </div>
              <div style={{ background: 'var(--paper-warm)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', height: 420, overflow: 'hidden' }}>
                <svg viewBox={`0 0 ${svgW} ${svgH}`} style={{ width: '100%', height: '100%', transform: `scale(${zoom})`, transformOrigin: 'center' }}>
                  {/* Edges */}
                  {edges.map((edge, idx) => {
                    const p1 = positions[edge.source] || [svgW/2, svgH/2];
                    const p2 = positions[edge.target] || [svgW/2, svgH/2];
                    return (
                      <line key={idx} x1={p1[0]} y1={p1[1]} x2={p2[0]} y2={p2[1]} stroke={getRelColor(edge.relation)} strokeWidth="1.2" strokeDasharray={edge.relation === 'applies' ? '4 3' : 'none'} opacity={0.45} />
                    );
                  })}
                  {/* Nodes */}
                  {nodes.map((node) => {
                    const [x, y] = positions[node.id] || [svgW/2, svgH/2];
                    const isCase = node.type === 'case';
                    const isSection = node.type === 'section';
                    const isSelected = selectedCase?.case_id === node.id || selectedCase?.id === node.id;
                    const r = isSelected ? 24 : isCase ? 18 : 14;
                    return (
                      <g key={node.id} onClick={() => { if (isCase) { setSelectedCase(node); } }} style={{ cursor: isCase ? 'pointer' : 'default' }}>
                        <circle cx={x} cy={y} r={r} fill={isSection ? 'var(--gold-deep)' : isSelected ? 'var(--legal-blue)' : 'var(--legal-blue-light)'} opacity={isSelected ? 1 : 0.85} />
                        {isSelected && <circle cx={x} cy={y} r={r + 4} fill="none" stroke="var(--legal-blue)" strokeWidth="2" strokeDasharray="4 3" opacity="0.5" />}
                        <text x={x} y={y + 3} textAnchor="middle" fill="#fff" fontSize={isCase ? "8" : "7"} fontWeight="600">
                          {isCase ? (node.citations || '') : '§'}
                        </text>
                        <text x={x} y={y + r + 12} textAnchor="middle" fill="var(--ink)" fontSize="7" fontWeight="500" fontFamily="var(--font-heading)">
                          {(node.label || '').length > 18 ? node.label.substring(0, 18) + '…' : node.label}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
              <div style={{ display: 'flex', gap: 16, marginTop: 10, justifyContent: 'center' }}>
                {[
                  { color: 'var(--legal-blue)', label: 'Cases', type: 'dot' },
                  { color: 'var(--gold-deep)', label: 'Shared Sections', type: 'dot' },
                  { color: 'var(--legal-blue)', label: 'Cites', type: 'line' },
                  { color: 'var(--gold-deep)', label: 'Cited By', type: 'line' },
                  { color: 'var(--status-ok)', label: 'Applies', type: 'dash' },
                ].map((l, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--ink-muted)' }}>
                    {l.type === 'dot' ? (
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: l.color }} />
                    ) : (
                      <span style={{ width: 16, height: 2, background: l.color, borderRadius: 1, ...(l.type === 'dash' ? { borderTop: '2px dashed', background: 'none', borderColor: l.color } : {}) }} />
                    )}
                    {l.label}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search Results */}
          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>
                {cases.length > 0 ? `Search Results (${cases.length})` : 'Search for Cases'}
              </h2>
              {cases.length > 0 && (
                <div style={{ display: 'flex', gap: 6 }}>
                  <button onClick={handleExportPDF} disabled={exporting} className="btn-ghost" style={{ fontSize: 11, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Download size={11} /> PDF
                  </button>
                  <button onClick={handleExportCSV} disabled={exporting} className="btn-ghost" style={{ fontSize: 11, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Download size={11} /> CSV
                  </button>
                </div>
              )}
            </div>
            {cases.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {cases.map((c) => (
                  <div
                    key={c.case_id}
                    onClick={() => { setSelectedCase(c); loadCaseGraph(c.case_id); }}
                    className="glass-card-lift"
                    style={{
                      padding: '14px 16px',
                      background: selectedCase?.case_id === c.case_id ? 'var(--paper-deep)' : 'var(--paper)',
                      border: `1px solid ${selectedCase?.case_id === c.case_id ? 'var(--gold)' : 'var(--border)'}`,
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                      <h4 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.3 }}>{c.name || c.case_name}</h4>
                      <span className={`badge ${c.relevance === 'High' ? 'badge-ok' : c.relevance === 'Medium' ? 'badge-warn' : 'badge-gold'}`}>{c.relevance}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 11, color: 'var(--ink-faint)', marginBottom: 6 }}>
                      <span><Scale size={10} style={{ display: 'inline', verticalAlign: 'middle' }} /> {c.court}</span>
                      <span><MapPin size={10} style={{ display: 'inline', verticalAlign: 'middle' }} /> {c.state}</span>
                      <span><Calendar size={10} style={{ display: 'inline', verticalAlign: 'middle' }} /> {c.year}</span>
                      <span>{c.citations} citations</span>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {c.sections?.slice(0, 3).map((s, i) => (
                        <span key={i} style={{ fontSize: 10, padding: '2px 8px', background: 'var(--status-info-bg)', color: 'var(--status-info)', borderRadius: 99, fontWeight: 600 }}>{s}</span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 12 }}>
                      <span style={{ color: 'var(--ink-faint)' }}>Similarity: <strong style={{ color: 'var(--legal-blue)' }}>{c.similarity}%</strong></span>
                      <span style={{ color: 'var(--ink-faint)' }}>Strength: <strong style={{ color: 'var(--gold-deep)' }}>{c.precedent_score || c.precedent_strength}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 32 }}>
                <Network size={40} color="var(--ink-subtle)" style={{ opacity: 0.3, marginBottom: 12 }} />
                <p style={{ color: 'var(--ink-faint)', fontSize: 13 }}>Enter a query above to search 7,000+ legal cases</p>
                <p style={{ color: 'var(--ink-subtle)', fontSize: 11, marginTop: 8 }}>Try: "murder", "IPC 420", "bail", "property dispute"</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div>
          {selectedCase ? (
            <div className="glass-card animate-fade-in" style={{ padding: 24, position: 'sticky', top: 24 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16 }}>Case Details</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div>
                  <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Case Name</p>
                  <p style={{ fontWeight: 700, color: 'var(--ink)', fontSize: 15, lineHeight: 1.3 }}>{selectedCase.name || selectedCase.case_name || selectedCase.label}</p>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase' }}>Court</p>
                    <span className="badge badge-info">{selectedCase.court || 'N/A'}</span>
                  </div>
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase' }}>Year</p>
                    <span className="badge badge-gold">{selectedCase.year || 'N/A'}</span>
                  </div>
                </div>
                {selectedCase.outcome && (
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase' }}>Outcome</p>
                    <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--status-ok)' }}>{selectedCase.outcome}</p>
                  </div>
                )}
                {selectedCase.summary && (
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Summary</p>
                    <p style={{ fontSize: 12, color: 'var(--ink-light)', lineHeight: 1.6 }}>{selectedCase.summary}</p>
                  </div>
                )}
                <div>
                  <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 6 }}>Precedent Strength</p>
                  <p style={{ fontWeight: 800, fontSize: 28, color: 'var(--legal-blue)', fontFamily: 'var(--font-heading)' }}>{selectedCase.precedent_strength || selectedCase.precedent_score || '—'}</p>
                  <div className="progress-bar" style={{ marginTop: 4 }}>
                    <div className="progress-info" style={{ width: `${selectedCase.precedent_strength || selectedCase.precedent_score || 0}%` }} />
                  </div>
                </div>
                {selectedCase.sections?.length > 0 && (
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 6 }}>Legal Sections</p>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {selectedCase.sections.map((s, i) => (
                        <span key={i} style={{ fontSize: 11, padding: '3px 10px', background: 'var(--status-info-bg)', color: 'var(--status-info)', borderRadius: 99, fontWeight: 600 }}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {selectedCase.key_issues?.length > 0 && (
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 6 }}>Key Issues</p>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {selectedCase.key_issues.map((issue, i) => (
                        <span key={i} style={{ fontSize: 11, padding: '3px 10px', background: 'var(--paper-deep)', color: 'var(--ink-muted)', borderRadius: 99, border: '1px solid var(--border)' }}>{issue}</span>
                      ))}
                    </div>
                  </div>
                )}
                {selectedCase.judges?.length > 0 && (
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Bench</p>
                    {selectedCase.judges.map((j, i) => (
                      <p key={i} style={{ fontSize: 12, color: 'var(--ink-light)' }}><Users size={10} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />{j}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-card" style={{ padding: 32, textAlign: 'center' }}>
              <Network size={40} color="var(--ink-subtle)" style={{ opacity: 0.4, marginBottom: 12 }} />
              <p style={{ color: 'var(--ink-faint)', fontSize: 13 }}>Search and click a case to view full details</p>
            </div>
          )}

          {/* Graph Metrics */}
          {graphData?.metrics && (
            <div className="glass-card" style={{ padding: 16, marginTop: 16 }}>
              <h4 style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Graph Metrics</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  { label: 'Total Nodes', val: graphData.metrics.total_nodes },
                  { label: 'Connections', val: graphData.metrics.total_connections },
                  { label: 'Case Nodes', val: graphData.metrics.case_nodes },
                  { label: 'Shared Sections', val: graphData.metrics.section_nodes },
                ].map((m, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                    <span style={{ color: 'var(--ink-muted)' }}>{m.label}</span>
                    <strong style={{ color: 'var(--ink)' }}>{m.val}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
