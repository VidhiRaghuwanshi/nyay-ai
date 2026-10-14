import { useState, useEffect, useCallback } from 'react';
import { Clock, TrendingUp, Loader2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import PageHeader from '../components/PageHeader';
import { proceduralAPI } from '../services/api';

export default function ProceduralFlow() {
  const [caseType, setCaseType] = useState('criminal');
  const [court, setCourt] = useState('district');
  const [state, setState] = useState('delhi');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendData, setBackendData] = useState(null);

  const fallbackTimeline = {
    criminal: {
      stages: [
        { stage: 'FIR Filing', duration: 1, delayProb: 5 },
        { stage: 'Investigation', duration: 3, delayProb: 15 },
        { stage: 'First Hearing', duration: 2, delayProb: 35 },
        { stage: 'Chargesheet', duration: 2, delayProb: 20 },
        { stage: 'Evidence', duration: 8, delayProb: 45 },
        { stage: 'Arguments', duration: 3, delayProb: 30 },
        { stage: 'Judgment', duration: 1, delayProb: 25 }
      ],
      totalMonths: 20,
      delayLikelihood: 65
    },
    civil: {
      stages: [
        { stage: 'Filing', duration: 1, delayProb: 8 },
        { stage: 'Admission', duration: 2, delayProb: 40 },
        { stage: 'Evidence', duration: 12, delayProb: 50 },
        { stage: 'Arguments', duration: 4, delayProb: 35 },
        { stage: 'Judgment', duration: 2, delayProb: 40 }
      ],
      totalMonths: 21,
      delayLikelihood: 72
    }
  };

  const fetchTimeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await proceduralAPI.predict(caseType, court, state);
      if (result && !result.error) {
        setBackendData({
          stages: result.stages?.map(s => ({
            stage: s.stage,
            duration: s.duration,
            delayProb: s.delay_probability || s.delay_prob
          })) || [],
          totalMonths: result.expected_duration,
          delayLikelihood: result.delay_probability,
          worstCase: result.worst_case_duration,
          delayFactors: result.delay_factors,
          stageWiseRisk: result.stage_wise_risk,
          dataEvidence: result.data_evidence
        });
      }
    } catch (err) {
      console.error('Timeline prediction failed:', err);
      setError('Backend offline. Showing default timeline data.');
      setBackendData(null);
    } finally {
      setLoading(false);
    }
  }, [caseType, court, state]);

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  // Use backend data if available, else fallback
  const currentData = backendData || fallbackTimeline[caseType];

  const delayFactorsData = backendData?.delayFactors
    ? Object.entries(backendData.delayFactors).map(([name, value]) => ({
        name: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value,
        impact: value > 25 ? 'High' : value > 15 ? 'Medium' : 'Low'
      }))
    : [
        { name: 'Court Backlog', value: 35, impact: 'High' },
        { name: 'Judge Availability', value: 25, impact: 'High' },
        { name: 'Adjournments', value: 20, impact: 'Medium' },
        { name: 'Evidence Complexity', value: 15, impact: 'Medium' },
        { name: 'Other', value: 5, impact: 'Low' }
      ];

  const COLORS = ['var(--legal-blue)', 'var(--gold-deep)', 'var(--burgundy)', '#6B5B95', 'var(--ink-subtle)'];
  const CHART_COLORS = ['#2E4057', '#C9A84C', '#8B2635', '#6B5B95', '#B8B8C4'];

  const chartData = currentData.stages.map(s => ({
    ...s,
    fill: s.delayProb >= 40 ? '#8B2635' : s.delayProb >= 20 ? '#C9A84C' : '#2D6A4F'
  }));

  return (
    <div className="animate-fade-in">
      <PageHeader
        icon={Clock}
        title="Procedural Flow Engine"
        description="Predict case timeline, delays, and judicial process durations"
        accentColor="#6B5B95"
      />

      {error && (
        <div style={{ padding: '10px 16px', background: 'var(--status-warn-bg)', border: '1px solid rgba(176,140,26,0.2)', borderRadius: 'var(--radius-md)', marginBottom: 16, fontSize: 13, color: 'var(--status-warn)' }}>
          ⚠️ {error}
        </div>
      )}

      {/* Filters */}
      <div className="glass-card" style={{ padding: 20, marginBottom: 24 }}>
        <div className="stats-grid-3">
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Case Type</label>
            <select value={caseType} onChange={(e) => setCaseType(e.target.value)} className="select-ink">
              <option value="criminal">Criminal</option>
              <option value="civil">Civil</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Court Level</label>
            <select value={court} onChange={(e) => setCourt(e.target.value)} className="select-ink">
              <option value="district">District Court</option>
              <option value="high">High Court</option>
              <option value="supreme">Supreme Court</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>State</label>
            <select value={state} onChange={(e) => setState(e.target.value)} className="select-ink">
              <option value="delhi">Delhi</option>
              <option value="mumbai">Mumbai</option>
              <option value="bangalore">Bangalore</option>
              <option value="chennai">Chennai</option>
              <option value="kolkata">Kolkata</option>
            </select>
          </div>
        </div>
      </div>

      {/* Prediction Cards */}
      <div className="stats-grid-3" style={{ marginBottom: 24 }}>
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Expected Duration</span>
            {loading ? <Loader2 size={18} color="#6B5B95" className="animate-spin" /> : <Clock size={18} color="#6B5B95" />}
          </div>
          <p style={{ fontSize: 36, fontWeight: 800, color: '#6B5B95', fontFamily: 'var(--font-heading)' }}>{currentData.totalMonths}</p>
          <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>months</p>
        </div>
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Delay Probability</span>
            <TrendingUp size={18} color="var(--status-danger)" />
          </div>
          <p style={{ fontSize: 36, fontWeight: 800, color: 'var(--status-danger)', fontFamily: 'var(--font-heading)' }}>{currentData.delayLikelihood}%</p>
          <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>likelihood of delays</p>
        </div>
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Worst Case</span>
            <Clock size={18} color="var(--gold-deep)" />
          </div>
          <p style={{ fontSize: 36, fontWeight: 800, color: 'var(--gold-deep)', fontFamily: 'var(--font-heading)' }}>{backendData?.worstCase || Math.round(currentData.totalMonths * 1.5)}</p>
          <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>months (with delays)</p>
        </div>
      </div>

      <div className="page-grid">
        {/* Left */}
        <div>
          {/* Bar Chart */}
          <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16 }}>Case Timeline by Stage</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="stage" stroke="var(--ink-faint)" tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} angle={-30} textAnchor="end" height={80} />
                <YAxis stroke="var(--ink-faint)" tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--ink)', border: 'none', borderRadius: 8, color: '#fff' }} labelStyle={{ color: '#fff' }} />
                <Bar dataKey="duration" fill="var(--legal-blue)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            {/* Stage cards */}
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${currentData.stages.length}, 1fr)`, gap: 6, marginTop: 16 }}>
              {currentData.stages.map((stage, idx) => (
                <div key={idx} style={{ padding: 8, background: 'var(--paper-warm)', borderRadius: 'var(--radius-sm)', textAlign: 'center', border: '1px solid var(--border)' }}>
                  <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', fontFamily: 'var(--font-heading)' }}>{stage.duration}mo</p>
                  <p style={{ fontSize: 9, color: 'var(--ink-faint)', marginTop: 2 }}>{stage.stage}</p>
                  <p style={{ fontSize: 10, color: stage.delayProb >= 40 ? 'var(--status-danger)' : stage.delayProb >= 20 ? 'var(--status-warn)' : 'var(--status-ok)', fontWeight: 600, marginTop: 2 }}>
                    ⚠ {stage.delayProb}%
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Pie Chart */}
          <div className="glass-card" style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16 }}>Delay Contributing Factors</h2>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={delayFactorsData} cx="50%" cy="50%" outerRadius={90} innerRadius={50} dataKey="value" label={({ value }) => `${value}%`} labelLine={{ stroke: 'var(--ink-subtle)' }}>
                  {delayFactorsData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: 'var(--ink)', border: 'none', borderRadius: 8, color: '#fff' }} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginTop: 8 }}>
              {delayFactorsData.map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--ink-muted)' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: CHART_COLORS[i] }} /> {f.name}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div>
          <div className="glass-card" style={{ padding: 20, marginBottom: 20, position: 'sticky', top: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>Contributing Factors</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {delayFactorsData.map((factor) => (
                <div key={factor.name} style={{ padding: 12, background: 'var(--paper)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>{factor.name}</span>
                    <span className={`badge ${factor.impact === 'High' ? 'badge-danger' : factor.impact === 'Medium' ? 'badge-warn' : 'badge-info'}`}>{factor.impact}</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-bar-fill progress-info" style={{ width: `${factor.value}%` }} />
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>{factor.value}% of delays</p>
                </div>
              ))}
            </div>
          </div>

          {backendData?.dataEvidence && (
            <div className="glass-card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 10 }}>Dataset Evidence</h3>
              <p style={{ fontSize: 11, color: 'var(--ink-faint)', marginBottom: 12 }}>
                Estimates use the matching public NDAP backlog row instead of a static timeline.
              </p>
              {[
                ['Pending cases', backendData.dataEvidence.pending_cases?.toLocaleString()],
                ['Cases aged 5+ years', backendData.dataEvidence.aged_cases?.toLocaleString()],
                ['Monthly instituted', backendData.dataEvidence.monthly_instituted?.toLocaleString()],
                ['Monthly disposed', backendData.dataEvidence.monthly_disposed?.toLocaleString()],
              ].map(([label, value]) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--border)', fontSize: 12 }}>
                  <span style={{ color: 'var(--ink-muted)' }}>{label}</span>
                  <strong style={{ color: 'var(--ink)' }}>{value ?? '—'}</strong>
                </div>
              ))}
              <p style={{ fontSize: 10, color: 'var(--ink-faint)', marginTop: 10 }}>Source: {backendData.dataEvidence.source}</p>
            </div>
          )}

          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>Stage-wise Delay Risk</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {currentData.stages.map((stage, idx) => (
                <div key={idx} style={{ padding: 10, background: 'var(--paper)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>{stage.stage}</span>
                    <span className={`badge ${stage.delayProb >= 40 ? 'badge-danger' : stage.delayProb >= 20 ? 'badge-warn' : 'badge-ok'}`}>{stage.delayProb}%</span>
                  </div>
                  <div className="progress-bar" style={{ height: 4 }}>
                    <div className={`progress-bar-fill ${stage.delayProb >= 40 ? 'progress-danger' : stage.delayProb >= 20 ? 'progress-gold' : 'progress-ok'}`} style={{ width: `${stage.delayProb}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
