import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ArrowRight,
  ArrowUp,
  AlertTriangle,
  Briefcase,
  CalendarDays,
  FileText,
  Network,
  Search,
  Upload,
  Users,
  Zap,
  Bot,
  ChevronRight,
  Scale,
} from 'lucide-react';
import { chatbotAPI, legaltechAPI, outcomeAPI, precedentAPI, proceduralAPI, riskDetectorAPI } from '../services/api';

const emptyCase = {
  title: 'New case',
  court: 'Court not detected',
  state: 'State not detected',
  judge: 'Judge not detected',
  plaintiff: 'Plaintiff not detected',
  defendant: 'Defendant not detected',
  caseType: 'Case type not detected',
  summary: 'Upload one or more case documents to automatically detect parties, court, timeline, risks, and legal issues.',
  timeline: [],
  risks: [{ level: 'Low', title: 'Waiting for case material', description: 'Upload documents or enter case facts to start automatic analysis.' }],
  riskFactors: [],
  precedents: [],
  metrics: { overallRisk: 0, winProbability: 0, evidenceQuality: 0, proceduralScore: 0 },
};

const getCaseTypeFilter = (type) => {
  if (/criminal|bail/i.test(type)) return 'Criminal';
  if (/property/i.test(type)) return 'Property';
  if (/family/i.test(type)) return 'Family';
  if (/commercial|contract/i.test(type)) return 'Commercial';
  return 'Civil';
};

const buildTimeline = (text) => {
  const lines = (text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const datePattern = /\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b/i;
  const datedEvents = lines.map((line) => ({ line, match: line.match(datePattern) })).filter((item) => item.match).slice(0, 8);

  if (datedEvents.length) {
    return datedEvents.map(({ line, match }, index) => ({
      date: match[0],
      label: line.replace(match[0], '').replace(/^[-:|\s]+|[-:|\s]+$/g, '').slice(0, 120) || `Document event ${index + 1}`,
      type: index === 0 ? 'start' : /hearing|order|judgment|decision/i.test(line) ? 'critical' : 'warning',
    }));
  }

  const lower = (text || '').toLowerCase();
  const stages = [
    { date: 'Case intake', label: 'Case material uploaded and indexed', type: 'start' },
    { date: 'Pleadings and notice', label: lower.includes('notice') ? 'Notice or service details found in the record' : 'Notice and pleadings require verification', type: 'warning' },
    { date: 'Evidence review', label: lower.includes('evidence') || lower.includes('witness') ? 'Evidence and witness references found in the record' : 'Evidence and witness record requires review', type: 'warning' },
    { date: 'Hearing or decision', label: lower.includes('hearing') || lower.includes('judgment') || lower.includes('order') ? 'Hearing or order references found in the record' : 'Hearing and decision dates are not stated', type: 'critical' },
  ];
  return stages;
};

const buildLegalSummary = (text, metadata = {}) => {
  const lower = (text || '').toLowerCase();
  const lines = (text || '').split(/\r?\n/).map((line) => line.replace(/\s+/g, ' ').trim()).filter(Boolean);
  const versusIndex = lines.findIndex((line) => /^(versus|vs\.?)$/i.test(line));
  const inlineVersus = /([^\r\n]{2,120})\s+\b(?:versus|vs\.?)\b\s+([^\r\n]{2,140})/i.exec(text || '');
  const titlePagePlaintiff = versusIndex > 0 ? lines[versusIndex - 1] : inlineVersus?.[1]?.trim();
  const titlePageDefendant = versusIndex >= 0 ? lines[versusIndex + 1] : inlineVersus?.[2]?.trim();
  const isUsableParty = (value) => value && value.length < 140 && !/not detected|case file|contractual relationship|the defendant disputes/i.test(value);

  const plaintiff = isUsableParty(titlePagePlaintiff) ? titlePagePlaintiff : metadata.plaintiff && metadata.plaintiff !== 'Not detected' ? metadata.plaintiff : /(?:plaintiff|petitioner|appellant)\s*[:-]\s*([^\r\n]+)/i.exec(text)?.[1]?.trim() || 'Plaintiff not detected';
  const defendant = isUsableParty(titlePageDefendant) ? titlePageDefendant : metadata.defendant && metadata.defendant !== 'Not detected' ? metadata.defendant : /(?:defendant|respondent|accused)\s*[:-]\s*([^\r\n]+)/i.exec(text)?.[1]?.trim() || 'Defendant not detected';
  const judge = metadata.judge && metadata.judge !== 'Not detected' ? metadata.judge : /(?:judge|before)\s*[:-]\s*([^\r\n]+)/i.exec(text)?.[1]?.trim() || 'Judge not detected';
  const court = metadata.court && metadata.court !== 'Not detected' ? metadata.court : /court(?: name)?\s*[:-]\s*([^\r\n]+)/i.exec(text)?.[1]?.trim() || 'Court not detected';
  const state = metadata.state && metadata.state !== 'Not detected' ? metadata.state : /state\s*[:-]\s*([^\r\n]+)/i.exec(text)?.[1]?.trim() || 'State not detected';

  const type = lower.includes('criminal')
    ? 'Criminal Matter'
    : lower.includes('bail')
      ? 'Bail Application'
      : lower.includes('contract') || lower.includes('agreement')
        ? 'Civil Contract Dispute'
        : 'Civil Matter';

  const timeline = buildTimeline(text);

  const riskList = [];
  if (lower.includes('notice') || lower.includes('legal notice')) {
    riskList.push({ level: 'High', title: 'Notice compliance', description: 'The record should confirm that notice service and timing satisfy procedural requirements.' });
  }
  if (lower.includes('default') || lower.includes('delay') || lower.includes('adjournment')) {
    riskList.push({ level: 'Medium', title: 'Delay risk', description: 'Adjournments or non-compliance may slow the matter and reduce strategic leverage.' });
  }
  if (lower.includes('agreement') || lower.includes('contract') || lower.includes('fee')) {
    riskList.push({ level: 'Medium', title: 'Document trail', description: 'Agreement, invoices, and proof of performance should be checked for gaps.' });
  }
  if (riskList.length === 0) {
    riskList.push({ level: 'Low', title: 'Review needed', description: 'The case has no critical risk flag from the initial scan, but document verification is still required.' });
  }

  return {
    title: `${plaintiff} v. ${defendant}`,
    court,
    state,
    judge,
    plaintiff,
    defendant,
    caseType: type,
    summary: 'The system auto-detected a likely legal issue pattern and flagged the main procedural and evidentiary risks for review.',
    timeline,
    risks: riskList,
    riskFactors: [],
    precedents: [],
    metrics: {
      overallRisk: 0,
      winProbability: 0,
      evidenceQuality: 0,
      proceduralScore: 0,
    },
  };
};

function CaseGraph({ graphData, caseTitle }) {
  const sourceNodes = graphData?.nodes || [];
  const sourceEdges = graphData?.edges || [];
  const caseNodes = sourceNodes.filter((node) => node.type === 'case').slice(0, 10);
  const sectionNodes = sourceNodes.filter((node) => node.type === 'section').slice(0, 8);
  const nodes = [
    { id: 'uploaded-case', label: caseTitle || 'Uploaded case', type: 'current' },
    ...caseNodes,
    ...sectionNodes,
  ];
  const nodeIds = new Set(nodes.map((node) => node.id));
    const edges = [
      ...caseNodes.slice(0, 6).map((node) => ({ source: 'uploaded-case', target: node.id, relation: 'similar' })),
      ...sourceEdges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)),
    ];
  const positions = { 'uploaded-case': [330, 175] };

  caseNodes.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(caseNodes.length, 1) - Math.PI / 2;
    positions[node.id] = [330 + 145 * Math.cos(angle), 175 + 105 * Math.sin(angle)];
  });
  sectionNodes.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(sectionNodes.length, 1) - Math.PI / 4;
    positions[node.id] = [330 + 245 * Math.cos(angle), 175 + 155 * Math.sin(angle)];
  });

  if (!caseNodes.length) {
    return <p className="panel-empty">Similar cases will appear after the case record is analyzed.</p>;
  }

  const relationColor = (relation) => relation === 'cites'
    ? '#3D5A80'
    : relation === 'cited_by'
      ? '#A68A3E'
      : '#2D6A4F';

  return (
    <div className="case-graph-wrap">
      <div className="case-graph-meta">
        <span>{caseNodes.length} similar cases</span>
        <span>{sectionNodes.length} shared sections</span>
        <span>{edges.length} connections</span>
      </div>
      <div className="case-graph-canvas">
        <svg viewBox="0 0 660 350" role="img" aria-label="Case precedent graph">
          {edges.map((edge, index) => {
            const start = positions[edge.source];
            const end = positions[edge.target];
            if (!start || !end) return null;
            return <line key={`${edge.source}-${edge.target}-${index}`} x1={start[0]} y1={start[1]} x2={end[0]} y2={end[1]} stroke={relationColor(edge.relation)} strokeWidth="1.5" strokeDasharray={edge.relation === 'applies' ? '5 4' : undefined} opacity="0.48" />;
          })}
          {nodes.map((node) => {
            const [x, y] = positions[node.id];
            const current = node.type === 'current';
            const section = node.type === 'section';
            const radius = current ? 30 : section ? 19 : 23;
            return (
              <g key={node.id}>
                <circle cx={x} cy={y} r={radius + 5} fill="none" stroke={current ? '#C9A84C' : section ? '#C9A84C' : '#3D5A80'} strokeWidth="1" opacity="0.22" />
                <circle cx={x} cy={y} r={radius} fill={current ? '#1A1A2E' : section ? '#C9A84C' : '#3D5A80'} />
                <text x={x} y={y + 4} textAnchor="middle" fill="#fff" fontSize={current ? 10 : 8} fontWeight="700">{current ? 'CASE' : section ? '§' : node.citations || '•'}</text>
                <text x={x} y={y + radius + 15} textAnchor="middle" fill="#1A1A2E" fontSize="9" fontWeight="600">
                  {(node.label || '').length > 24 ? `${node.label.slice(0, 24)}...` : node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="case-graph-legend">
        <span><i className="graph-key current" /> Uploaded case</span>
        <span><i className="graph-key precedent" /> Similar precedent</span>
        <span><i className="graph-key section" /> Shared legal section</span>
      </div>
    </div>
  );
}

export default function CaseWorkspace() {
  const [searchParams] = useSearchParams();
  const isNewCase = searchParams.get('new') === '1';
  const selectedCaseId = searchParams.get('case');
  const freshCaseId = searchParams.get('fresh');
  const [generatedConversationId] = useState(() => `case_${Date.now()}`);
  const conversationId = selectedCaseId || (freshCaseId ? `case_${freshCaseId}` : generatedConversationId);
  const [files, setFiles] = useState([]);
  const [documentMetadata, setDocumentMetadata] = useState({});
  const [caseData, setCaseData] = useState(emptyCase);
  const [caseText, setCaseText] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [analysisError, setAnalysisError] = useState('');
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [chatInput, setChatInput] = useState('What are the main risks in this case?');
  const [chatHistory, setChatHistory] = useState([]);
  const [chronologyEvents, setChronologyEvents] = useState([]);

  useEffect(() => {
    if (!isNewCase) {
      const savedCases = JSON.parse(localStorage.getItem('legalai_cases') || '[]');
      const legacyCase = localStorage.getItem('legalai_active_case');
      const savedCase = savedCases.find((item) => item.id === selectedCaseId) || (selectedCaseId ? null : savedCases[0]) || (legacyCase ? JSON.parse(legacyCase) : null);
      if (savedCase) {
        try {
          setCaseText(savedCase.caseText || '');
          setFiles((savedCase.files || []).map((name) => ({ name })));
          setDocumentMetadata(savedCase.metadata || {});
          setChatHistory([]);
          setChronologyEvents(savedCase.chronologyEvents || []);
        } catch {
          localStorage.removeItem('legalai_cases');
        }
      }
    }
  }, [isNewCase, selectedCaseId]);

  useEffect(() => {
    if (isNewCase) {
      setFiles([]);
      setCaseText('');
      setCaseData(emptyCase);
      setGraphData({ nodes: [], edges: [] });
      setDocumentMetadata({});
      setChatHistory([]);
      setChronologyEvents([]);
    }
  }, [isNewCase, freshCaseId]);

  useEffect(() => {
    if (!caseText.trim()) {
      setCaseData(emptyCase);
      return;
    }
    const autoSummary = buildLegalSummary(caseText, documentMetadata);
    setCaseData((prev) => ({ ...prev, ...autoSummary }));

    if (caseText.trim()) {
      const savedCase = {
        id: conversationId,
        caseText,
        files: files.map((file) => file.name),
        metadata: documentMetadata,
        chronologyEvents,
        title: autoSummary.title,
        updatedAt: new Date().toISOString(),
      };
      const existingCases = JSON.parse(localStorage.getItem('legalai_cases') || '[]');
      const nextCases = [savedCase, ...existingCases.filter((item) => item.id !== conversationId && item.caseText !== caseText)].slice(0, 20);
      localStorage.setItem('legalai_cases', JSON.stringify(nextCases));
      localStorage.setItem('legalai_active_case', JSON.stringify(savedCase));
      window.dispatchEvent(new Event('legalai-case-saved'));
    }
  }, [caseText, files, conversationId, documentMetadata, chronologyEvents]);

  useEffect(() => {
    if (!caseText.trim()) return undefined;
    let cancelled = false;
    const loadAnalysis = async () => {
      setAnalysisLoading(true);
      setAnalysisError('');
      try {
        const caseType = getCaseTypeFilter(caseData.caseType);
        const [riskResult, precedentResult] = await Promise.all([
          riskDetectorAPI.analyze(caseText, caseType.toLowerCase()),
          precedentAPI.search(caseText.slice(0, 3000), caseType),
        ]);
        if (cancelled) return;
        const evidenceQuality = Math.max(
          0,
          Math.min(100, 100 - Number(riskResult.overall_risk_score || 0)),
        );
        const precedentStrength = Math.max(
          0,
          Math.min(100, (precedentResult.similar_cases || []).length * 15),
        );
        const [outcomeResult, proceduralResult] = await Promise.all([
          outcomeAPI.predict({
            case_type: caseType,
            evidence_quality: evidenceQuality,
            precedent_strength: precedentStrength,
            description: caseText.slice(0, 6000),
          }),
          proceduralAPI.predict(
            caseType,
            caseData.court && caseData.court !== 'Court not detected' ? caseData.court : 'district',
            caseData.state && caseData.state !== 'State not detected' ? caseData.state : 'Delhi',
          ),
        ]);
        if (cancelled) return;
        setCaseData((prev) => ({
          ...prev,
          riskFactors: riskResult.risk_factors || [],
          risks: (riskResult.issues || []).length
            ? riskResult.issues.map((issue) => ({
              level: issue.severity === 'high' ? 'High' : issue.severity === 'medium' ? 'Medium' : 'Low',
              title: issue.title,
              description: `${issue.description} Recommended action: ${issue.suggestion}`,
            }))
            : [{ level: riskResult.risk_level || 'Low', title: 'No major automated trigger', description: 'The record was scanned without a critical issue being detected.' }],
          precedents: precedentResult.similar_cases || [],
          metrics: {
            ...prev.metrics,
            overallRisk: Math.round(riskResult.overall_risk_score || 0),
            winProbability: Math.round(outcomeResult.win_probability || 0),
            evidenceQuality,
            proceduralScore: Math.max(
              0,
              Math.min(100, Math.round(100 - (proceduralResult.delay_probability || 0))),
            ),
          },
        }));
        setGraphData(precedentResult.graph || { nodes: [], edges: [] });
      } catch (error) {
        if (!cancelled) setAnalysisError(error.response?.data?.detail || 'Case analysis is unavailable. Check that the backend is running.');
      } finally {
        if (!cancelled) setAnalysisLoading(false);
      }
    };
    loadAnalysis();
    return () => { cancelled = true; };
  }, [caseText, caseData.caseType, caseData.court, caseData.state]);

  const handleFiles = async (selectedFiles) => {
    const nextFiles = Array.from(selectedFiles || []);
    if (!nextFiles.length) return;
    setFiles(nextFiles);
    setUploadError('Uploading and extracting case files...');

    try {
      const results = await Promise.allSettled(nextFiles.map((file) => chatbotAPI.uploadDocument(file, conversationId)));
      const uploads = results.filter((result) => result.status === 'fulfilled').map((result) => result.value);
      const failures = results.filter((result) => result.status === 'rejected');
      const combinedText = uploads.map((upload) => upload.text || '').filter(Boolean).join('\n\n--- FILE ---\n\n');
      const metadata = uploads.map((upload) => upload.metadata || {}).find((item) => Object.values(item).some((value) => value && value !== 'Not detected')) || {};

      if (combinedText.trim()) {
        let extractedEvents = [];
        try {
          const chronologyResult = await legaltechAPI.extractChronology(
            { matter_id: conversationId, text: combinedText },
          );
          extractedEvents = chronologyResult.events || [];
          setChronologyEvents(extractedEvents);
        } catch (chronologyError) {
          setUploadError(`Files uploaded, but chronology extraction failed: ${chronologyError.response?.data?.detail || 'check the backend connection.'}`);
        }
        setDocumentMetadata(metadata);
        setCaseText(combinedText);
        if (!failures.length && extractedEvents.length) {
          setUploadError(`${uploads.length} file(s) uploaded and saved. ${extractedEvents.length} chronology event(s) found.`);
        } else if (failures.length) {
          setUploadError(`${uploads.length} file(s) uploaded. ${failures.length} file(s) failed. ${extractedEvents.length} chronology event(s) found.`);
        }
      } else {
        const reason = failures[0]?.reason;
        throw new Error(reason?.response?.data?.detail || reason?.message || 'No readable text was extracted.');
      }
    } catch (error) {
      setUploadError(`Upload failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleChat = async () => {
    const question = chatInput.trim();
    if (!question || !caseText.trim()) return;
    try {
      const result = await chatbotAPI.ask(question, { case_data: caseText, chat_history: chatHistory }, conversationId);
      const answer = `${result.content || result.response || 'The assistant returned no answer.'}${result.quota_notice ? `\n\nNote: ${result.quota_notice}` : ''}`;
      setChatHistory((previous) => [...previous, { question, answer }]);
      setChatInput('');
    } catch (error) {
      setChatHistory((previous) => [...previous, { question, answer: `Chat unavailable: ${error.response?.data?.detail || 'check that the backend and Google AI service are running.'}` }]);
    }
  };

  const displayedTimeline = chronologyEvents.length
    ? chronologyEvents.map((event) => ({
      date: event.date_text,
      label: event.description,
      type: event.event_type === 'court_event' ? 'critical' : event.event_type === 'filing' ? 'start' : 'warning',
    }))
    : caseData.timeline;

  return (
    <div className="animate-fade-in">
      <div className="workspace-header">
        <div>
          <div className="badge badge-gold">Legal Case Workspace</div>
          <h1 className="workspace-title">{caseData.title}</h1>
          <p className="workspace-subtitle">
            {caseData.court} • {caseData.state} • {caseData.caseType}
          </p>
        </div>

      </div>

      <div className="workspace-shell">
        <main className="workspace-main">
          <section className="case-tools">
            <div className="glass-card upload-panel">
              <div className="section-kicker"><Upload size={16} /> Upload Case Documents</div>
              <label className="upload-box">
                <Upload size={22} />
                <strong>Upload multiple files</strong>
                <span>PDF, DOCX, or TXT files</span>
                <input type="file" multiple onChange={(e) => handleFiles(e.target.files)} />
              </label>
              <div className="file-chip-list">
                {files.length ? files.map((file, idx) => (
                  <span key={idx} className="file-chip">{file.name}</span>
                )) : <span className="file-chip muted">No files uploaded</span>}
              </div>
              {uploadError && <p className="upload-status">{uploadError}</p>}
            </div>

            <div className="glass-card ai-panel">
              <div className="section-kicker"><Bot size={16} /> Case-Aware AI Assistant</div>
              <p className="chat-helper">Ask a question about the uploaded case record.</p>
              <div className="chat-transcript">
                {chatHistory.length ? chatHistory.map((turn, index) => (
                  <div key={`${turn.question}-${index}`} className="chat-turn">
                    <div className="chat-question"><strong>You</strong><p>{turn.question}</p></div>
                    <div className="chat-answer"><strong>Nyay AI</strong><p>{turn.answer}</p></div>
                  </div>
                )) : null}
              </div>
              <div className="chat-composer">
                <div className="chat-input-wrap">
                  <textarea value={chatInput} onChange={(e) => setChatInput(e.target.value)} rows={3} placeholder="Ask another question about this case..." onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      handleChat();
                    }
                  }} />
                  <button className="chat-send-button" onClick={handleChat} aria-label="Send question" title="Send question">
                    <ArrowUp size={18} />
                  </button>
                </div>
              </div>
              {files.length > 0 && <div className="source-pill-row">
                <span className="source-pill">Based on {files.length} case file{files.length === 1 ? '' : 's'}</span>
              </div>}
            </div>
          </section>

          <section className="panel-grid">
            <div className="metric-card glass-card">
              <div className="metric-label">Overall Risk</div>
              <div className="metric-value">{caseData.metrics.overallRisk}%</div>
              <div className="progress-bar"><div className="progress-bar-fill progress-danger" style={{ width: `${caseData.metrics.overallRisk}%` }} /></div>
            </div>

            <div className="metric-card glass-card">
              <div className="metric-label">Win Probability</div>
              <div className="metric-value">{caseData.metrics.winProbability}%</div>
              <div className="progress-bar"><div className="progress-bar-fill progress-ok" style={{ width: `${caseData.metrics.winProbability}%` }} /></div>
            </div>

            <div className="metric-card glass-card">
              <div className="metric-label">Evidence Quality</div>
              <div className="metric-value">{caseData.metrics.evidenceQuality}%</div>
              <div className="progress-bar"><div className="progress-bar-fill progress-gold" style={{ width: `${caseData.metrics.evidenceQuality}%` }} /></div>
            </div>

            <div className="metric-card glass-card">
              <div className="metric-label">Procedural Score</div>
              <div className="metric-value">{caseData.metrics.proceduralScore}%</div>
              <div className="progress-bar"><div className="progress-bar-fill progress-info" style={{ width: `${caseData.metrics.proceduralScore}%` }} /></div>
            </div>
          </section>

          <section className="info-grid">
            <div className="glass-card info-card">
              <div className="section-kicker"><Users size={14} /> Parties</div>
              <div className="party-box">
                <div><span>Petitioner</span><strong>{caseData.plaintiff}</strong></div>
                <div><span>Respondent</span><strong>{caseData.defendant}</strong></div>
                <div><span>Judge</span><strong>{caseData.judge}</strong></div>
              </div>
            </div>

            <div className="glass-card info-card">
              <div className="section-kicker"><CalendarDays size={14} /> Timeline</div>
              <div className="timeline-list">
                {displayedTimeline.length ? displayedTimeline.map((item, idx) => (
                  <div key={idx} className={`timeline-item ${item.type}`}>
                    <span className="timeline-dot" />
                    <div><strong>{item.date}</strong><p>{item.label}</p></div>
                  </div>
                )) : <p className="panel-empty">Timeline appears after documents are uploaded.</p>}
              </div>
            </div>
          </section>

          <section className="content-grid">
            <div className="glass-card content-panel">
              <div className="section-kicker"><AlertTriangle size={14} /> Auto Risk Warnings</div>
              {analysisLoading && <p className="analysis-note">Calculating risk from the case record...</p>}
              {analysisError && <p className="analysis-error">{analysisError}</p>}
              <div className="risk-list">
                {caseData.risks.map((risk, idx) => (
                  <div key={idx} className="risk-item">
                    <div className={`risk-badge ${risk.level.toLowerCase()}`}>{risk.level}</div>
                    <div>
                      <strong>{risk.title}</strong>
                      <p>{risk.description}</p>
                    </div>
                  </div>
                ))}
              </div>
              {caseData.riskFactors.length > 0 && <div className="risk-factor-list">
                <div className="risk-factor-heading">Risk calculation points</div>
                {caseData.riskFactors.map((factor, idx) => (
                  <div key={idx} className="risk-factor">
                    <div><strong>{factor.name}</strong><p>{factor.description}</p></div>
                    <span>{factor.score}%</span>
                  </div>
                ))}
              </div>}
            </div>

            <div className="glass-card content-panel">
              <div className="section-kicker"><Network size={14} /> Precedent Graph</div>
              <CaseGraph graphData={graphData} caseTitle={caseData.title} />
            </div>
          </section>

        </main>

      </div>
    </div>
  );
}
