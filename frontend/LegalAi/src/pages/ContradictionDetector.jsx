import { useState } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle, Trash2, Loader2 } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { riskDetectorAPI } from '../services/api';

export default function ContradictionDetector() {
  const [caseText, setCaseText] = useState('');
  const [analyzed, setAnalyzed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [riskScore, setRiskScore] = useState(0);
  const [riskLevel, setRiskLevel] = useState('');
  const [issues, setIssues] = useState([]);
  const [counterArguments, setCounterArguments] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  const handleAnalyze = async () => {
    if (caseText.trim().length < 20) return;
    setLoading(true);
    setError(null);

    try {
      const result = await riskDetectorAPI.analyze(caseText, 'criminal');

      if (result && !result.error) {
        setRiskScore(Math.round(result.overall_risk_score || 0));
        setRiskLevel(result.risk_level || '');
        setIssues(result.issues || []);
        setCounterArguments(
          (result.counter_arguments || []).map((ca, idx) => ({
            id: idx + 1,
            argument: ca.argument,
            likelihood: Math.round(ca.likelihood)
          }))
        );
        setRecommendations(result.recommendations || []);
        setAnalyzed(true);
      } else {
        throw new Error(result?.error || 'Analysis failed');
      }
    } catch (err) {
      console.error('Risk analysis failed:', err);
      setError(err.response?.data?.detail || 'Backend analysis failed. Start the backend and try again.');
      setAnalyzed(false);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = () => {
    if (riskScore >= 70) return 'var(--status-danger)';
    if (riskScore >= 40) return 'var(--status-warn)';
    return 'var(--status-ok)';
  };

  const getRiskLabel = () => {
    if (riskLevel) return riskLevel + ' Risk';
    if (riskScore >= 70) return 'High Risk';
    if (riskScore >= 40) return 'Medium Risk';
    return 'Low Risk';
  };

  const getSeverityBadge = (severity) => {
    if (severity === 'high') return 'badge-danger';
    if (severity === 'medium') return 'badge-warn';
    return 'badge-info';
  };

  const getSeverityBorder = (severity) => {
    if (severity === 'high') return 'var(--status-danger)';
    if (severity === 'medium') return 'var(--status-warn)';
    return 'var(--legal-blue)';
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        icon={AlertTriangle}
        title="Contradiction & Risk Detector"
        description="Detect weaknesses, contradictions, and missing elements in your case arguments"
        accentColor="var(--burgundy)"
      />

      {error && (
        <div style={{ padding: '10px 16px', background: 'var(--status-warn-bg)', border: '1px solid rgba(176,140,26,0.2)', borderRadius: 'var(--radius-md)', marginBottom: 16, fontSize: 13, color: 'var(--status-warn)' }}>
          ⚠️ {error}
        </div>
      )}

      <div className="page-grid">
        {/* Left */}
        <div>
          {/* Input */}
          <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 12 }}>Enter Case Details</h2>
            <textarea
              value={caseText}
              onChange={(e) => setCaseText(e.target.value)}
              placeholder="Paste your FIR, petition, or case summary here. The AI will detect contradictions, missing elements, and weak points..."
              className="textarea-ink"
              style={{ height: 220 }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
              <button onClick={handleAnalyze} className="btn-ink" style={{ flex: 1, background: 'var(--burgundy)' }} disabled={loading || caseText.trim().length < 20}>
                {loading ? <Loader2 size={15} className="animate-spin" /> : <AlertTriangle size={15} />} {loading ? 'Analyzing...' : 'Analyze for Risks'}
              </button>
              <button onClick={() => { setCaseText(''); setAnalyzed(false); setError(null); }} className="btn-ghost" style={{ padding: '10px 14px' }}>
                <Trash2 size={15} />
              </button>
            </div>
          </div>

          {analyzed && (
            <>
              {/* Issues */}
              <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertTriangle size={18} color="var(--burgundy)" /> Detected Issues ({issues.length})
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {issues.map((issue) => (
                    <div key={issue.id} style={{
                      padding: 16,
                      background: 'var(--paper)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)',
                      borderLeft: `4px solid ${getSeverityBorder(issue.severity)}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>{issue.title}</h3>
                        <span className={`badge ${getSeverityBadge(issue.severity)}`}>{issue.severity}</span>
                      </div>
                      <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginBottom: 10 }}>{issue.description}</p>
                      <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 8 }}>
                        📍 <strong>{issue.location}</strong>
                      </div>
                      <div style={{
                        padding: '8px 12px',
                        background: 'var(--paper-warm)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 12,
                        color: 'var(--gold-deep)',
                        fontWeight: 500
                      }}>
                        💡 {issue.suggestion}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Counter Arguments */}
              <div className="glass-card" style={{ padding: 24 }}>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={18} color="var(--burgundy)" /> Possible Counter Arguments
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {counterArguments.map((arg) => (
                    <div key={arg.id} style={{ padding: 16, background: 'var(--paper)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                      <p style={{ fontSize: 13, color: 'var(--ink)', marginBottom: 10, lineHeight: 1.5 }}>{arg.argument}</p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600 }}>Attack Likelihood:</span>
                        <div className="progress-bar" style={{ flex: 1 }}>
                          <div className={`progress-bar-fill ${arg.likelihood >= 70 ? 'progress-danger' : 'progress-gold'}`} style={{ width: `${arg.likelihood}%` }} />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)', fontFamily: 'var(--font-mono)' }}>{arg.likelihood}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right Panel */}
        <div>
          {analyzed ? (
            <>
              {/* Risk Score */}
              <div className="glass-card" style={{ padding: 24, marginBottom: 20, textAlign: 'center', position: 'sticky', top: 24 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 16 }}>Overall Risk Score</h3>
                <div style={{
                  width: 120,
                  height: 120,
                  borderRadius: '50%',
                  background: `conic-gradient(${getRiskColor()} ${riskScore * 3.6}deg, var(--paper-deep) 0deg)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <div style={{
                    width: 96,
                    height: 96,
                    borderRadius: '50%',
                    background: 'var(--paper-card)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <span style={{ fontSize: 28, fontWeight: 800, color: getRiskColor(), fontFamily: 'var(--font-heading)' }}>{riskScore}</span>
                    <span style={{ fontSize: 10, color: 'var(--ink-faint)' }}>/ 100</span>
                  </div>
                </div>
                <h4 style={{ fontSize: 18, fontWeight: 700, color: 'var(--ink)', marginBottom: 6 }}>{getRiskLabel()}</h4>
                <p style={{ fontSize: 12, color: 'var(--ink-muted)' }}>
                  {riskScore >= 70 ? '⚠️ Significant improvements needed' : riskScore >= 40 ? '⚡ Address key issues' : '✅ Generally safe'}
                </p>
              </div>

              {/* Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
                <div className="glass-card" style={{ padding: 14, textAlign: 'center' }}>
                  <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>High</p>
                  <p style={{ fontSize: 22, fontWeight: 800, color: 'var(--status-danger)', fontFamily: 'var(--font-heading)' }}>{issues.filter(i => i.severity === 'high').length}</p>
                </div>
                <div className="glass-card" style={{ padding: 14, textAlign: 'center' }}>
                  <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Medium</p>
                  <p style={{ fontSize: 22, fontWeight: 800, color: 'var(--status-warn)', fontFamily: 'var(--font-heading)' }}>{issues.filter(i => i.severity === 'medium').length}</p>
                </div>
              </div>

              {/* Recommendations */}
              <div className="glass-card" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle size={15} color="var(--status-ok)" /> Recommendations
                </h3>
                <ol style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {recommendations.map((rec, i) => (
                    <li key={i} style={{ display: 'flex', gap: 8, fontSize: 12, color: 'var(--ink-muted)', lineHeight: 1.4 }}>
                      <span style={{ fontWeight: 700, color: 'var(--status-ok)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>{i + 1}.</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </>
          ) : (
            <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
              <AlertTriangle size={44} color="var(--ink-subtle)" style={{ opacity: 0.3, marginBottom: 12 }} />
              <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>Enter case details and click analyze to get risk assessment</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
