import { useEffect, useState } from 'react';
import { CheckCircle2, FileSignature, Loader2, ShieldCheck, Upload } from 'lucide-react';
import { legaltechAPI } from '../services/api';

const TENANT_HEADERS = {
  'X-Organization-ID': 'org-demo',
  'X-User-ID': 'user-demo',
};

const readAsBase64 = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
  reader.onerror = () => reject(new Error('The selected file could not be read.'));
  reader.readAsDataURL(file);
});

export default function ClientPortal() {
  const [file, setFile] = useState(null);
  const [documentName, setDocumentName] = useState('');
  const [document, setDocument] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [signature, setSignature] = useState({
    signer_name: '',
    signer_email: '',
    signature_text: '',
  });
  const [signedRecord, setSignedRecord] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const loadDocuments = async () => {
    try {
      const result = await legaltechAPI.listPortalDocuments(TENANT_HEADERS);
      setDocuments(result.documents || []);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Portal documents could not be loaded.');
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const uploadDocument = async () => {
    if (!file) {
      setError('Select a PDF or document before uploading.');
      return;
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const contentBase64 = await readAsBase64(file);
      const created = await legaltechAPI.createPortalDocument({
        name: documentName.trim() || file.name,
        content_base64: contentBase64,
        mime_type: file.type || 'application/octet-stream',
      }, TENANT_HEADERS);
      setDocument(created);
      setDocuments((previous) => [created, ...previous]);
      setSignedRecord(null);
      setMessage('Document uploaded and is ready for signature.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Document upload failed.');
    } finally {
      setLoading(false);
    }
  };

  const downloadDocument = async (selectedDocument) => {
    setError('');
    try {
      const blob = await legaltechAPI.downloadPortalDocument(selectedDocument.id, TENANT_HEADERS);
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = selectedDocument.name || 'portal-document';
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Document download failed.');
    }
  };

  const signDocument = async (event) => {
    event.preventDefault();
    if (!document) {
      setError('Upload a document before signing.');
      return;
    }
    if (!signature.signer_name.trim() || !signature.signature_text.trim()) {
      setError('Signer name and signature text are required.');
      return;
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const signed = await legaltechAPI.signPortalDocument(document.id, signature, TENANT_HEADERS);
      setSignedRecord(signed);
      setDocument((previous) => ({ ...previous, status: 'signed' }));
      setMessage('Document signature recorded.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Document signing failed.');
    } finally {
      setLoading(false);
    }
  };

  const updateSignature = (key, value) => {
    setSignature((previous) => ({ ...previous, [key]: value }));
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <div className="section-kicker"><ShieldCheck size={14} /> Client portal</div>
          <h1 className="page-title">Secure document signing</h1>
          <p className="page-subtitle">Upload a document, review its integrity hash, and record a tenant-scoped signature.</p>
        </div>
      </div>

      {message && <p className="upload-status">{message}</p>}
      {error && <p className="error-message">{error}</p>}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 20 }}>
        <section className="panel">
          <div className="panel-title"><Upload size={15} /> Upload portal document</div>
          <label className="field-label" htmlFor="portal-name">Document name</label>
          <input
            id="portal-name"
            className="input-ink"
            value={documentName}
            onChange={(event) => setDocumentName(event.target.value)}
            placeholder="Client agreement"
          />
          <label className="field-label" htmlFor="portal-file">Document file</label>
          <input
            id="portal-file"
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button className="btn-primary" type="button" onClick={uploadDocument} disabled={loading}>
            {loading ? <Loader2 size={16} className="spin" /> : <Upload size={16} />}
            Upload document
          </button>

          {document && (
            <div style={{ marginTop: 20, padding: 14, background: 'var(--paper-deep)', borderRadius: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
                <FileSignature size={16} /> {document.name}
              </div>
              <p className="panel-muted">Status: {document.status}</p>
              <p style={{ fontSize: 11, color: 'var(--ink-faint)', wordBreak: 'break-all' }}>
                SHA-256: {document.sha256}
              </p>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-title"><FileSignature size={15} /> Sign document</div>
          <form onSubmit={signDocument}>
            <label className="field-label" htmlFor="signer-name">Signer name</label>
            <input id="signer-name" className="input-ink" value={signature.signer_name} onChange={(event) => updateSignature('signer_name', event.target.value)} />
            <label className="field-label" htmlFor="signer-email">Signer email (optional)</label>
            <input id="signer-email" className="input-ink" type="email" value={signature.signer_email} onChange={(event) => updateSignature('signer_email', event.target.value)} />
            <label className="field-label" htmlFor="signature-text">Signature text</label>
            <input id="signature-text" className="input-ink" value={signature.signature_text} onChange={(event) => updateSignature('signature_text', event.target.value)} placeholder="Type your legal name" />
            <button className="btn-secondary" type="submit" disabled={loading || !document}>
              {loading ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
              Record signature
            </button>
          </form>

          {signedRecord && (
            <div style={{ marginTop: 20, padding: 14, border: '1px solid var(--border)', borderRadius: 8 }}>
              <strong>Signature recorded</strong>
              <p className="panel-muted">Signed by {signedRecord.signer_name} on {new Date(signedRecord.signed_at).toLocaleString()}.</p>
              <p style={{ fontSize: 11, color: 'var(--ink-faint)', wordBreak: 'break-all' }}>
                Signature hash: {signedRecord.signature_hash}
              </p>
            </div>
          )}
        </section>
      </div>

      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel-title"><FileSignature size={15} /> Portal documents</div>
        {documents.length === 0 ? (
          <p className="panel-muted">No tenant documents have been uploaded yet.</p>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {documents.map((item) => (
              <div key={item.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: 12, border: '1px solid var(--border)', borderRadius: 8 }}>
                <div>
                  <strong>{item.name}</strong>
                  <p className="panel-muted">{item.status} · {new Date(item.created_at).toLocaleString()}</p>
                </div>
                <button className="btn-secondary" type="button" onClick={() => downloadDocument(item)}>
                  Download
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
