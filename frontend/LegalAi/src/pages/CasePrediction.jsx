import { useState, useEffect } from 'react';
import { Gauge, BarChart3, TrendingUp, Clock, AlertTriangle, CheckCircle, Loader2, ArrowRight, Users } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { predictionAPI } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const CASE_TYPES = ['Criminal', 'Civil', 'Family', 'Commercial', 'Property'];
const COURT_LEVELS = ['District', 'High', 'Supreme'];
const STATES = ['Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Uttar Pradesh'];

const RISK_COLORS = { High: 'var(--status-danger)', Medium: 'var(--status-warn)', Low: 'var(--status-ok)' };
const PIE_COLORS = ['#C9A84C', '#2E4057', '#2D6A4F', '#8B2635', '#6B5B95'];

export default function CasePrediction() {
  const [form, setForm] = useState({ case_type: 'Criminal', court_level: 'District', state: 'Delhi', hearings: '', workload: '' });
  const [prediction, setPrediction] = useState(null);
  const [stats, setStats] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [data, evaluationData] = await Promise.all([
          predictionAPI.getStats(),
          predictionAPI.getEvaluation(),
        ]);
        setStats(data);
        setEvaluation(evaluationData);
      } catch { /* ignore */ }
    };
    fetchStats();
  }, []);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await predictionAPI.predict(
        form.case_type,
        form.court_level,
        form.state,
        form.hearings ? parseInt(form.hearings) : undefined,
        form.workload ? parseInt(form.workload) : undefined,
      );
      setPrediction(data);
    } catch (err) {
      setError('Prediction failed. Backend may be offline.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const riskColor = prediction ? RISK_COLORS[prediction.risk_level] || 'var(--ink-muted)' : 'var(--ink-muted)';

  return (
    <div className="animate-fade-in">
      <PageHeader
        icon={Gauge}
        title="Case Prediction Engine"
        description="Predict case delay duration and success probability using ML analysis of 10,000+ judicial cases"
        accentColor="#6B5B95"
      />

      {error && (
        <div style={{ padding: '10px 16px', background: 'var(--status-warn-bg)', border: '1px solid rgba(176,140,26,0.2)', borderRadius: 'var(--radius-md)', marginBottom: 16, fontSize: 13, color: 'var(--status-warn)' }}>
          {error}
        </div>
      )}

      <div className="page-grid-left">

        {/* Left - Input Form */}
        <div>
          <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <BarChart3 size={18} color="#6B5B95" /> Case Parameters
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block' }}>Case Type</label>
                <select className="select-ink" value={form.case_type} onChange={(e) => setForm({ ...form, case_type: e.target.value })}>
                  {CASE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block' }}>Court Level</label>
                <select className="select-ink" value={form.court_level} onChange={(e) => setForm({ ...form, court_level: e.target.value })}>
                  {COURT_LEVELS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block' }}>State</label>
                <select className="select-ink" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })}>
                  {STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block' }}>Hearings (opt.)</label>
                  <input type="number" className="input-ink" placeholder="e.g. 15" value={form.hearings} onChange={(e) => setForm({ ...form, hearings: e.target.value })} />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block' }}>Workload (opt.)</label>
                  <input type="number" className="input-ink" placeholder="e.g. 400" value={form.workload} onChange={(e) => setForm({ ...form, workload: e.target.value })} />
                </div>
              </div>

              <button className="btn-ink" onClick={handlePredict} disabled={loading} style={{ width: '100%', marginTop: 4, background: '#6B5B95' }}>
                {loading ? <Loader2 size={16} className="animate-spin" /> : <Gauge size={16} />}
                {loading ? 'Analyzing...' : 'Predict Case Outcome'}
              </button>
            </div>
          </div>


        </div>

        {/* Right - Results */}
        <div>
          {prediction ? (
            <div className="animate-fade-in">
              {/* Hero Prediction Cards */}
              <div className="stats-grid-3" style={{ marginBottom: 20 }}>
                {/* Predicted Delay */}
                <div className="glass-card" style={{ padding: 24, textAlign: 'center', borderTop: `3px solid ${riskColor}` }}>
                  <Clock size={24} color={riskColor} style={{ marginBottom: 8 }} />
                  <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Predicted Delay</p>
                  <p style={{ fontSize: 36, fontWeight: 900, fontFamily: 'var(--font-heading)', color: riskColor, lineHeight: 1 }}>{prediction.predicted_delay_months}</p>
                  <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginTop: 4 }}>months</p>
                </div>

                {/* Success Rate */}
                <div className="glass-card" style={{ padding: 24, textAlign: 'center', borderTop: '3px solid var(--status-ok)' }}>
                  <TrendingUp size={24} color="var(--status-ok)" style={{ marginBottom: 8 }} />
                  <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Success Rate</p>
                  <p style={{ fontSize: 36, fontWeight: 900, fontFamily: 'var(--font-heading)', color: 'var(--status-ok)', lineHeight: 1 }}>{prediction.success_rate}%</p>
                  <div className="progress-bar" style={{ marginTop: 8 }}>
                    <div className="progress-ok" style={{ width: `${prediction.success_rate}%` }} />
                  </div>
                </div>

                {/* Risk Level */}
                <div className="glass-card" style={{ padding: 24, textAlign: 'center', borderTop: `3px solid ${riskColor}` }}>
                  <AlertTriangle size={24} color={riskColor} style={{ marginBottom: 8 }} />
                  <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Risk Level</p>
                  <span className={`badge ${prediction.risk_level === 'High' ? 'badge-danger' : prediction.risk_level === 'Medium' ? 'badge-warn' : 'badge-ok'}`} style={{ fontSize: 14, padding: '6px 16px' }}>
                    {prediction.risk_level}
                  </span>
                  <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 8 }}>
                    Confidence: <strong>{prediction.confidence}%</strong>
                  </p>
                  <p style={{ fontSize: 11, color: 'var(--ink-subtle)', marginTop: 2 }}>
                    Based on {prediction.sample_size} cases
                  </p>
                </div>
              </div>

              {/* Contributing Factors */}
              <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16 }}>Contributing Factors</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {prediction.contributing_factors?.map((f, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ width: 120, fontSize: 13, fontWeight: 600, color: 'var(--ink-light)', flexShrink: 0 }}>{f.factor}</div>
                      <div style={{ flex: 1 }}>
                        <div className="progress-bar" style={{ height: 8 }}>
                          <div style={{
                            height: '100%', borderRadius: 99, width: `${f.impact}%`,
                            background: f.direction === 'negative' ? 'linear-gradient(90deg, #9B2226, #E63946)' :
                              f.direction === 'positive' ? 'linear-gradient(90deg, #2D6A4F, #52B788)' :
                              'linear-gradient(90deg, var(--gold), var(--gold-light))',
                            transition: 'width 0.8s ease'
                          }} />
                        </div>
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 700, color: f.direction === 'negative' ? 'var(--status-danger)' : f.direction === 'positive' ? 'var(--status-ok)' : 'var(--gold-deep)', width: 40, textAlign: 'right' }}>{f.impact}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Stats + Chart */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                {/* Percentiles */}
                <div className="glass-card" style={{ padding: 24 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>Delay Distribution</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {[
                      { label: 'Best Case (25th)', val: prediction.percentiles?.p25 },
                      { label: 'Median (50th)', val: prediction.percentiles?.p50 },
                      { label: 'Typical (75th)', val: prediction.percentiles?.p75 },
                      { label: 'Worst Case (90th)', val: prediction.percentiles?.p90 },
                    ].map((p, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: i === 0 ? 'var(--status-ok-bg)' : i === 3 ? 'var(--status-danger-bg)' : 'var(--paper-warm)', borderRadius: 'var(--radius-sm)' }}>
                        <span style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{p.label}</span>
                        <strong style={{ fontSize: 14, color: 'var(--ink)' }}>{p.val} mo.</strong>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Case Type Breakdown Chart */}
                {stats?.by_case_type && (
                  <div className="glass-card" style={{ padding: 24 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>Avg. Delay by Case Type</h3>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={stats.by_case_type}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} />
                        <YAxis tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} />
                        <Tooltip
                          contentStyle={{ background: 'var(--ink)', border: 'none', borderRadius: 8, color: '#fff', fontSize: 12 }}
                          labelStyle={{ color: 'var(--gold-light)' }}
                        />
                        <Bar dataKey="avg_delay" radius={[4,4,0,0]}>
                          {stats.by_case_type.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Comparable Cases */}
              {evaluation?.evaluation_status === 'evaluated' && (
                <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 6 }}>Research Evaluation — Delay Model</h3>
                  <p style={{ fontSize: 11, color: 'var(--ink-faint)', marginBottom: 14 }}>
                    Deterministic holdout evaluation on {evaluation.dataset}; this is not an outcome win-rate metric.
                  </p>
                  <div className="stats-grid-4">
                    {[
                      ['MAE', `${evaluation.metrics.mae_months} mo.`],
                      ['RMSE', `${evaluation.metrics.rmse_months} mo.`],
                      ['R²', evaluation.metrics.r2],
                      ['Within ±6 mo.', `${Math.round(evaluation.metrics.within_6_months * 100)}%`],
                    ].map(([label, value]) => (
                      <div key={label} style={{ padding: 12, background: 'var(--paper-warm)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                        <p style={{ fontSize: 10, color: 'var(--ink-faint)', fontWeight: 700, textTransform: 'uppercase' }}>{label}</p>
                        <p style={{ fontSize: 20, fontWeight: 800, color: 'var(--legal-blue)', marginTop: 4 }}>{value}</p>
                      </div>
                    ))}
                  </div>
                  <p style={{ fontSize: 10, color: 'var(--ink-faint)', marginTop: 12 }}>
                    Train: {evaluation.train_size.toLocaleString()} · Test: {evaluation.test_size.toLocaleString()} · Split: {evaluation.split_method}
                  </p>
                </div>
              )}

              {/* Comparable Cases */}
              {prediction.comparable_cases?.length > 0 && (
                <div className="glass-card" style={{ padding: 24 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>
                    <Users size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} />
                    Comparable Cases from Dataset
                  </h3>
                  <div style={{ overflowX: 'auto' }}>
                    <table className="table-ink">
                      <thead>
                        <tr>
                          <th>Type</th>
                          <th>Court</th>
                          <th>State</th>
                          <th>Delay</th>
                          <th>Hearings</th>
                          <th>Disposal</th>
                          <th>Match</th>
                        </tr>
                      </thead>
                      <tbody>
                        {prediction.comparable_cases.map((c, i) => (
                          <tr key={i}>
                            <td style={{ fontWeight: 600 }}>{c.case_type}</td>
                            <td>{c.court_level}</td>
                            <td>{c.state}</td>
                            <td><strong style={{ color: c.delay_months > 40 ? 'var(--status-danger)' : c.delay_months > 20 ? 'var(--status-warn)' : 'var(--status-ok)' }}>{c.delay_months} mo.</strong></td>
                            <td>{c.hearings}</td>
                            <td>{(c.disposal_rate * 100).toFixed(0)}%</td>
                            <td><span className={`badge ${c.match_score >= 80 ? 'badge-ok' : c.match_score >= 50 ? 'badge-warn' : 'badge-gold'}`}>{c.match_score}%</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="glass-card" style={{ padding: 48, textAlign: 'center' }}>
              <Gauge size={48} color="var(--ink-subtle)" style={{ opacity: 0.3, marginBottom: 16 }} />
              <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--ink-muted)', marginBottom: 8 }}>Configure Case Parameters</h3>
              <p style={{ fontSize: 14, color: 'var(--ink-faint)', maxWidth: 400, margin: '0 auto', lineHeight: 1.6 }}>
                Select case type, court level, and state, then click <strong>Predict</strong> to get AI-powered delay and success prediction based on 10,000+ real judicial cases.
              </p>

              {/* Quick stats cards */}
              {stats && (
                <div className="stats-grid-3" style={{ marginTop: 24, gap: 12 }}>
                  {stats.by_case_type?.slice(0, 3).map((t, i) => (
                    <div key={i} style={{ padding: 14, background: 'var(--paper-warm)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                      <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase' }}>{t.name}</p>
                      <p style={{ fontSize: 20, fontWeight: 800, color: 'var(--ink)', fontFamily: 'var(--font-heading)' }}>{t.avg_delay} mo.</p>
                      <p style={{ fontSize: 11, color: 'var(--ink-subtle)' }}>{t.count} cases</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
