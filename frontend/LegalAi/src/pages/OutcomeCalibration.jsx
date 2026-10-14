import { useState, useEffect } from 'react';
import { TrendingUp, BarChart3, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts';
import PageHeader from '../components/PageHeader';
import { outcomeAPI } from '../services/api';

export default function OutcomeCalibration() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [predictionData, setPredictionData] = useState(null);
  const [calibrationMetrics, setCalibrationMetrics] = useState(null);

  // Fetch outcome prediction and calibration on mount
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch prediction
        const prediction = await outcomeAPI.predict({
          case_type: 'criminal',
          evidence_quality: 70,
          precedent_strength: 80,
          description: 'Sample criminal case analysis'
        });
        if (prediction && !prediction.error) {
          setPredictionData(prediction);
        }

        // Fetch calibration metrics
        const calibration = await outcomeAPI.getCalibration();
        if (calibration) {
          setCalibrationMetrics(calibration);
        }
      } catch (err) {
        console.error('Outcome API failed:', err);
      setError(err.response?.data?.detail || 'Backend offline. Start the backend and try again.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Display only measured backend data; do not substitute simulated metrics.
  const caseMetrics = {
    winProbability: predictionData ? Math.round(predictionData.win_probability) : null,
    confidence: predictionData?.confidence_level || 'Unavailable',
    dataPoints: predictionData?.data_points_used || calibrationMetrics?.data_points || null,
    modelAccuracy: predictionData?.model_accuracy != null ? Math.round(predictionData.model_accuracy) : null,
    calibrationError: predictionData?.calibration_error != null
      ? (predictionData.calibration_error * 100).toFixed(1)
      : null
  };

  const calibrationData = [];
  const confidenceData = [];

  const outcomeBreakdown = predictionData?.outcome_distribution
    ? [
        { outcome: 'Plaintiff Wins', probability: Math.round(predictionData.outcome_distribution.plaintiff_win), color: 'var(--status-ok)' },
        { outcome: 'Defendant Wins', probability: Math.round(predictionData.outcome_distribution.defendant_win), color: 'var(--legal-blue)' },
        { outcome: 'Settlement', probability: Math.round(predictionData.outcome_distribution.settlement), color: 'var(--gold-deep)' },
        { outcome: 'Dismissal', probability: Math.round(predictionData.outcome_distribution.dismissal), color: 'var(--ink-muted)' }
      ]
    : [];

  const factors = predictionData?.factors || [];

  return (
    <div className="animate-fade-in">
      <PageHeader
        icon={TrendingUp}
        title="Outcome Calibration System"
        description="Confidence scorer and reliability metrics for case outcome predictions"
        accentColor="var(--gold-deep)"
      />

      {error && (
        <div style={{ padding: '10px 16px', background: 'var(--status-warn-bg)', border: '1px solid rgba(176,140,26,0.2)', borderRadius: 'var(--radius-md)', marginBottom: 16, fontSize: 13, color: 'var(--status-warn)' }}>
          ⚠️ {error}
        </div>
      )}

      {/* Metric Cards */}
      <div className="stats-grid-4" style={{ marginBottom: 24 }}>
        {[
          { label: 'Win Probability', value: `${caseMetrics.winProbability}%`, icon: TrendingUp, color: 'var(--gold-deep)' },
          { label: 'Confidence Level', value: caseMetrics.confidence, icon: CheckCircle, color: 'var(--status-ok)' },
          { label: 'Model Accuracy', value: caseMetrics.modelAccuracy != null ? `${caseMetrics.modelAccuracy}%` : 'Not evaluated', icon: BarChart3, color: 'var(--legal-blue)' },
          { label: 'Calibration Error', value: caseMetrics.calibrationError != null ? `${caseMetrics.calibrationError}%` : 'Not evaluated', icon: AlertTriangle, color: 'var(--status-warn)' },
        ].map((m, i) => {
          const Icon = m.icon;
          return (
            <div key={i} className="glass-card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{m.label}</span>
                {loading ? <Loader2 size={16} color={m.color} className="animate-spin" /> : <Icon size={16} color={m.color} />}
              </div>
              <p style={{ fontSize: 28, fontWeight: 800, color: m.color, fontFamily: 'var(--font-heading)' }}>{m.value}</p>
            </div>
          );
        })}
      </div>

      <div className="page-grid">
        {/* Left */}
        <div>
          {/* Calibration Curve */}
          <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 4 }}>Calibration Curve</h2>
            <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 16 }}>Predicted vs Actual Probability</p>
            {calibrationData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis type="number" dataKey="prediction" stroke="var(--ink-faint)" />
                  <YAxis type="number" dataKey="actual" stroke="var(--ink-faint)" />
                  <Tooltip contentStyle={{ background: 'var(--ink)', border: 'none', borderRadius: 8, color: '#fff' }} />
                  <Scatter data={calibrationData} fill="var(--gold-deep)" />
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ minHeight: 280, display: 'grid', placeItems: 'center', color: 'var(--ink-faint)', fontSize: 13, textAlign: 'center' }}>
                Calibration chart unavailable until labeled historical outcomes are loaded.
              </div>
            )}
          </div>

          {/* Confidence Distribution */}
          <div className="glass-card" style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 16 }}>Confidence Distribution</h2>
            {confidenceData.length > 0 ? <ResponsiveContainer width="100%" height={280}>
              <BarChart data={confidenceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" stroke="var(--ink-faint)" tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} />
                <YAxis stroke="var(--ink-faint)" tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--ink)', border: 'none', borderRadius: 8, color: '#fff' }} />
                <Legend wrapperStyle={{ paddingTop: 12, fontSize: 12 }} />
                <Bar dataKey="count" fill="var(--legal-blue)" name="Cases" radius={[4, 4, 0, 0]} />
                <Bar dataKey="accuracy" fill="var(--gold-deep)" name="Accuracy %" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer> : (
              <div style={{ minHeight: 280, display: 'grid', placeItems: 'center', color: 'var(--ink-faint)', fontSize: 13, textAlign: 'center' }}>
                Confidence distribution requires evaluated historical outcomes.
              </div>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div>
          {/* Assessment */}
          <div className="glass-card" style={{ padding: 20, marginBottom: 20, position: 'sticky', top: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>Assessment Details</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>Confidence Level</p>
                <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>{caseMetrics.confidence}</p>
                <p style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 2 }}>Reasonable confidence — use with caution</p>
              </div>
              <div>
                <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>Training Data</p>
                <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>{caseMetrics.dataPoints} cases</p>
              </div>
              <div>
                <p style={{ fontSize: 11, color: 'var(--ink-faint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Model Performance</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                      <span style={{ color: 'var(--ink-muted)' }}>Accuracy</span>
                      <span style={{ fontWeight: 700, color: 'var(--legal-blue)', fontFamily: 'var(--font-mono)' }}>{caseMetrics.modelAccuracy != null ? `${caseMetrics.modelAccuracy}%` : 'Not evaluated'}</span>
                    </div>
                    <div className="progress-bar"><div className="progress-bar-fill progress-info" style={{ width: `${caseMetrics.modelAccuracy || 0}%` }} /></div>
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                      <span style={{ color: 'var(--ink-muted)' }}>Calibration Quality</span>
                      <span style={{ fontWeight: 700, color: 'var(--status-ok)', fontFamily: 'var(--font-mono)' }}>{calibrationMetrics?.calibration_quality != null ? `${Math.round(calibrationMetrics.calibration_quality * 100)}%` : 'Not evaluated'}</span>
                    </div>
                    <div className="progress-bar"><div className="progress-bar-fill progress-ok" style={{ width: `${calibrationMetrics?.calibration_quality != null ? calibrationMetrics.calibration_quality * 100 : 0}%` }} /></div>
                  </div>
                </div>
              </div>
              <div style={{ padding: 10, background: 'var(--status-warn-bg)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(176,140,26,0.2)' }}>
                <p style={{ fontSize: 11, color: 'var(--status-warn)', lineHeight: 1.5 }}>⚠️ {caseMetrics.confidence} confidence means predictions should be confirmed with supplementary analysis.</p>
              </div>
            </div>
          </div>

          {/* Factors */}
          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>Prediction Factors</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {factors.map((f, i) => (
                <div key={i} style={{ padding: 10, background: 'var(--paper)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>{f.factor}</span>
                    <span className={`badge ${f.direction === 'positive' ? 'badge-ok' : f.direction === 'negative' ? 'badge-danger' : 'badge-info'}`}>
                      {f.direction === 'positive' ? '↑' : f.direction === 'negative' ? '↓' : '→'} {f.influence}%
                    </span>
                  </div>
                  <div className="progress-bar" style={{ height: 4 }}>
                    <div className={`progress-bar-fill ${f.direction === 'positive' ? 'progress-ok' : f.direction === 'negative' ? 'progress-danger' : 'progress-info'}`} style={{ width: `${f.influence}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Outcome Distribution */}
      <div className="glass-card" style={{ padding: 24, marginTop: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 20 }}>Predicted Outcome Distribution</h2>
        <div className="stats-grid-4">
          {outcomeBreakdown.map((o, i) => (
            <div key={i} style={{ padding: 20, background: 'var(--paper)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', textAlign: 'center' }}>
              <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', marginBottom: 10 }}>{o.outcome}</h4>
              <p style={{ fontSize: 28, fontWeight: 800, color: o.color, fontFamily: 'var(--font-heading)', marginBottom: 8 }}>{o.probability}%</p>
              <div className="progress-bar" style={{ marginBottom: 8 }}>
                <div className="progress-bar-fill" style={{ width: `${o.probability}%`, background: o.color }} />
              </div>
              <p style={{ fontSize: 11, color: 'var(--ink-faint)' }}>Probability derived from the current case inputs</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
