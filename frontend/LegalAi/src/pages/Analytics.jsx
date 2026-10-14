import { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart3, CheckCircle2, Clock3, Loader2, Plus, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { legaltechAPI } from '../services/api';

const TENANT_HEADERS = {
  'X-Organization-ID': 'org-demo',
  'X-User-ID': 'user-demo',
};

const initialOutcome = {
  matter_id: '',
  judge: '',
  opposing_counsel: '',
  outcome: '',
  resolution_days: '',
  settlement: false,
};

export default function Analytics() {
  const [groupBy, setGroupBy] = useState('judge');
  const [groups, setGroups] = useState([]);
  const [outcome, setOutcome] = useState(initialOutcome);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await legaltechAPI.getAnalytics(groupBy, TENANT_HEADERS);
      setGroups(result.groups || []);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Analytics could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [groupBy]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const totals = useMemo(() => groups.reduce((summary, group) => ({
    cases: summary.cases + Number(group.cases || 0),
    wins: summary.wins + Number(group.wins || 0),
    settlements: summary.settlements + Number(group.settlements || 0),
  }), { cases: 0, wins: 0, settlements: 0 }), [groups]);

  const updateOutcome = (key, value) => {
    setOutcome((previous) => ({ ...previous, [key]: value }));
  };

  const addOutcome = async (event) => {
    event.preventDefault();
    if (!outcome.matter_id.trim() || !outcome.outcome.trim()) {
      setError('Matter ID and outcome are required.');
      return;
    }
    setSaving(true);
    setError('');
    setMessage('');
    try {
      await legaltechAPI.addOutcome({
        ...outcome,
        matter_id: outcome.matter_id.trim(),
        judge: outcome.judge.trim() || null,
        opposing_counsel: outcome.opposing_counsel.trim() || null,
        resolution_days: outcome.resolution_days === '' ? null : Number(outcome.resolution_days),
      }, TENANT_HEADERS);
      setOutcome(initialOutcome);
      setMessage('Outcome record saved.');
      await loadAnalytics();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Outcome record could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const chartData = groups.map((group) => ({
    name: group.group.length > 22 ? `${group.group.slice(0, 22)}…` : group.group,
    winRate: group.win_rate,
    settlementRate: group.settlement_rate,
  }));

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <div className="section-kicker"><BarChart3 size={14} /> Case analytics</div>
          <h1 className="page-title">Judicial and counsel analytics</h1>
          <p className="page-subtitle">Summarize recorded outcomes by judge or opposing counsel. Results are based only on your tenant’s saved records.</p>
        </div>
      </div>

      {message && <p className="upload-status">{message}</p>}
      {error && <p className="error-message">{error}</p>}

      <div className="panel-grid" style={{ marginBottom: 20 }}>
        <div className="metric-card glass-card"><div className="metric-label">Recorded cases</div><div className="metric-value">{totals.cases}</div></div>
        <div className="metric-card glass-card"><div className="metric-label">Recorded wins</div><div className="metric-value">{totals.wins}</div></div>
        <div className="metric-card glass-card"><div className="metric-label">Settlements</div><div className="metric-value">{totals.settlements}</div></div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 20 }}>
        <section className="panel">
          <div className="panel-title"><Plus size={15} /> Record case outcome</div>
          <form onSubmit={addOutcome}>
            <label className="field-label" htmlFor="analytics-matter">Matter ID</label>
            <input id="analytics-matter" className="input-ink" value={outcome.matter_id} onChange={(event) => updateOutcome('matter_id', event.target.value)} />
            <label className="field-label" htmlFor="analytics-judge">Judge</label>
            <input id="analytics-judge" className="input-ink" value={outcome.judge} onChange={(event) => updateOutcome('judge', event.target.value)} />
            <label className="field-label" htmlFor="analytics-counsel">Opposing counsel</label>
            <input id="analytics-counsel" className="input-ink" value={outcome.opposing_counsel} onChange={(event) => updateOutcome('opposing_counsel', event.target.value)} />
            <label className="field-label" htmlFor="analytics-outcome">Outcome</label>
            <input id="analytics-outcome" className="input-ink" value={outcome.outcome} onChange={(event) => updateOutcome('outcome', event.target.value)} placeholder="win, loss, settled, dismissed..." />
            <label className="field-label" htmlFor="analytics-days">Resolution days</label>
            <input id="analytics-days" className="input-ink" type="number" min="0" value={outcome.resolution_days} onChange={(event) => updateOutcome('resolution_days', event.target.value)} />
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', margin: '14px 0', fontSize: 13 }}>
              <input type="checkbox" checked={outcome.settlement} onChange={(event) => updateOutcome('settlement', event.target.checked)} />
              Settlement reached
            </label>
            <button className="btn-primary" type="submit" disabled={saving}>
              {saving ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
              Save outcome
            </button>
          </form>
        </section>

        <section className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
            <div className="panel-title"><Users size={15} /> Grouped performance</div>
            <select className="select-ink" value={groupBy} onChange={(event) => setGroupBy(event.target.value)}>
              <option value="judge">By judge</option>
              <option value="opposing_counsel">By opposing counsel</option>
            </select>
          </div>
          {loading ? <div className="panel-empty"><Loader2 size={18} className="spin" /> Loading analytics...</div>
            : !groups.length ? <div className="panel-empty">No outcome records are available for this tenant yet.</div>
              : <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData} margin={{ top: 12, right: 10, left: 0, bottom: 28 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="name" angle={-20} textAnchor="end" height={55} tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="winRate" name="Win rate %" fill="#2D6A4F" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="settlementRate" name="Settlement rate %" fill="#C9A84C" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>}
        </section>
      </div>

      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel-title"><Clock3 size={15} /> Detailed groups</div>
        {!groups.length ? <div className="panel-empty">Add outcome records to see resolution-time summaries.</div> : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead><tr><th>Group</th><th>Cases</th><th>Wins</th><th>Win rate</th><th>Settlements</th><th>Settlement rate</th><th>Avg. resolution</th></tr></thead>
              <tbody>{groups.map((group) => (
                <tr key={group.group}>
                  <td>{group.group}</td>
                  <td>{group.cases}</td>
                  <td>{group.wins}</td>
                  <td>{group.win_rate}%</td>
                  <td>{group.settlements}</td>
                  <td>{group.settlement_rate}%</td>
                  <td>{group.average_resolution_days == null ? 'Not available' : `${group.average_resolution_days} days`}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
