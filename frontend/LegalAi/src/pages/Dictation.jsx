import { useRef, useState } from 'react';
import { FileAudio, Loader2, Mic, Upload } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { legaltechAPI } from '../services/api';

export default function Dictation() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  const submit = async () => {
    if (!file || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      setResult(await legaltechAPI.uploadDictation(file, {}, null));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Transcription failed. Check the backend configuration and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        icon={Mic}
        title="Speech-to-Legal Dictation"
        description="Transcribe an audio recording locally with Faster-Whisper and structure it into legal action sections."
        accentColor="var(--status-ok)"
      />

      <div className="page-grid-narrow">
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <FileAudio size={20} color="var(--gold-deep)" />
            <strong>Upload audio recording</strong>
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: 13, lineHeight: 1.6 }}>
            Audio is processed locally when <code>TRANSCRIPTION_PROVIDER=local</code>. The first upload may download the Whisper model.
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="audio/*,.wav,.mp3,.m4a,.webm,.mp4"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setResult(null);
              setError('');
            }}
            style={{ display: 'none' }}
          />
          <button className="btn-ghost" onClick={() => inputRef.current?.click()} style={{ marginTop: 12 }}>
            <Upload size={15} /> {file ? file.name : 'Choose audio file'}
          </button>
          <button className="btn-gold" onClick={submit} disabled={!file || loading} style={{ marginTop: 12, marginLeft: 10 }}>
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Mic size={15} />}
            {loading ? 'Transcribing...' : 'Transcribe and structure'}
          </button>
          {error && <div className="error-message" style={{ marginTop: 16 }}>{error}</div>}
        </div>

        {result && (
          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{ color: 'var(--ink-muted)', fontSize: 12, marginBottom: 12 }}>
              Source: {result.transcription_source}
            </div>
            <h3>Summary</h3>
            <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{result.summary}</p>
            {[
              ['Client Instructions', result.client_instructions],
              ['Court Directives', result.court_directives],
              ['Action Items', result.action_items],
            ].map(([title, items]) => (
              <section key={title} style={{ marginTop: 18 }}>
                <h3>{title}</h3>
                {items.length ? <ul>{items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}</ul> : <p style={{ color: 'var(--ink-muted)' }}>None detected.</p>}
              </section>
            ))}
            <details style={{ marginTop: 18 }}>
              <summary>Full transcript</summary>
              <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{result.transcript}</p>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
