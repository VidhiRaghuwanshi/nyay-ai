import { useMemo, useState } from 'react';
import { CalendarDays, FileUp, Loader2, Search } from 'lucide-react';
import { legaltechAPI } from '../services/api';

const TENANT_HEADERS = {
  'X-Organization-ID': 'org-demo',
  'X-User-ID': 'user-demo',
};

const eventColors = {
  court_event: '#7c3aed',
  filing: '#2563eb',
  investigation: '#dc2626',
  case_event: '#64748b',
};

export default function Chronology() {
  const [matterId, setMatterId] = useState('');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [events, setEvents] = useState([]);
  const [source, setSource] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => a.date_text.localeCompare(b.date_text)),
    [events],
  );

  const analyzeText = async () => {
    if (!matterId.trim() || !text.trim()) {
      setError('Enter a matter ID and evidence text first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await legaltechAPI.extractChronology(
        { matter_id: matterId.trim(), text: text.trim() },
        TENANT_HEADERS,
      );
      setEvents(result.events || []);
      setSource('typed evidence');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Chronology extraction failed.');
    } finally {
      setLoading(false);
    }
  };

  const uploadEvidence = async () => {
    if (!matterId.trim() || !file) {
      setError('Enter a matter ID and select an evidence file first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await legaltechAPI.uploadChronologyEvidence(
        matterId.trim(),
        file,
        TENANT_HEADERS,
      );
      setEvents(result.events || []);
      setSource(`${result.source} · ${result.filename}`);
      setText('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Evidence upload failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <div className="section-kicker"><CalendarDays size={14} /> Evidence chronology</div>
          <h1 className="page-title">Build a case timeline</h1>
          <p className="page-subtitle">
            Extract dated events, classify them, and review the source context saved for the matter.
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 20 }}>
        <section className="panel">
          <div className="panel-title">Evidence input</div>
          <label className="field-label" htmlFor="chronology-matter">Matter ID</label>
          <input
            id="chronology-matter"
            className="input-ink"
            value={matterId}
            onChange={(event) => setMatterId(event.target.value)}
            placeholder="e.g. MATTER-2026-001"
          />

          <label className="field-label" htmlFor="chronology-text">Paste evidence text</label>
          <textarea
            id="chronology-text"
            className="input-ink"
            rows={10}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Include dated filings, hearings, orders, investigation steps, and other case events..."
          />
          <button className="btn-primary" type="button" onClick={analyzeText} disabled={loading}>
            {loading ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
            Analyze text
          </button>

          <div style={{ borderTop: '1px solid var(--border)', margin: '22px 0', paddingTop: 18 }}>
            <label className="field-label" htmlFor="chronology-file">Upload PDF, DOCX, TXT, or MD</label>
            <input
              id="chronology-file"
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
            <button className="btn-secondary" type="button" onClick={uploadEvidence} disabled={loading}>
              {loading ? <Loader2 size={16} className="spin" /> : <FileUp size={16} />}
              Upload and extract
            </button>
          </div>
          {error && <p className="error-message">{error}</p>}
        </section>

        <section className="panel">
          <div className="panel-title">Extracted timeline</div>
          {source && <p className="panel-muted">Source: {source}</p>}
          {!sortedEvents.length ? (
            <div className="panel-empty">Timeline events will appear after analysis.</div>
          ) : (
            <div style={{ position: 'relative', paddingLeft: 24 }}>
              <div style={{
                position: 'absolute',
                left: 7,
                top: 8,
                bottom: 8,
                width: 2,
                background: 'var(--border)',
              }}
              />
              {sortedEvents.map((event) => (
                <article key={event.id || event._id} style={{ position: 'relative', paddingBottom: 20 }}>
                  <span style={{
                    position: 'absolute',
                    left: -22,
                    top: 4,
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    background: eventColors[event.event_type] || eventColors.case_event,
                    border: '2px solid var(--paper)',
                    boxShadow: '0 0 0 1px var(--border)',
                  }}
                  />
                  <div style={{ fontSize: 12, color: 'var(--gold-deep)', fontWeight: 700 }}>
                    {event.date_text}
                  </div>
                  <div style={{ fontWeight: 700, color: 'var(--ink)', marginTop: 3 }}>
                    {(event.event_type || 'case_event').replaceAll('_', ' ')}
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--ink-muted)', lineHeight: 1.55, margin: '5px 0 0' }}>
                    {event.description}
                  </p>
                  {event.entities?.length > 0 && (
                    <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 5 }}>
                      Entities: {event.entities.join(', ')}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
