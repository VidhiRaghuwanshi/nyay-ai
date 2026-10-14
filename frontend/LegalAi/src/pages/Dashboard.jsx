import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Network, AlertTriangle, Clock, MessageSquare, TrendingUp, FileText, ArrowRight, BarChart3, Shield, Scale, BookOpen, Wifi, WifiOff, Gauge, Sparkles, CheckCircle2, Users, Zap, ChevronRight } from 'lucide-react';
import StatCard from '../components/StatCard';
import { checkHealth } from '../services/api';

export default function Dashboard() {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const check = async () => {
      try {
        await checkHealth();
        setBackendStatus('connected');
      } catch {
        setBackendStatus('offline');
      }
    };
    check();
  }, []);

  // Auto-cycle through How It Works steps
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep(prev => (prev + 1) % 4);
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      id: 1,
      title: 'Precedent Search',
      description: 'Find relevant past judgments and citation networks instantly — powered by legal knowledge graphs.',
      icon: Network,
      path: '/precedent-graph',
      accent: 'var(--legal-blue)',
      tag: 'Knowledge Graph'
    },
    {
      id: 2,
      title: 'Risk & Contradiction Scan',
      description: 'Automatically detect weak arguments, contradictions, and missing evidence before court submission.',
      icon: AlertTriangle,
      path: '/contradiction',
      accent: 'var(--burgundy)',
      tag: 'Risk Analysis'
    },
    {
      id: 3,
      title: 'Timeline Estimator',
      description: 'Know how long your case will take — get data-backed predictions on judicial timelines and delays.',
      icon: Clock,
      path: '/procedural',
      accent: '#6B5B95',
      tag: 'Timeline'
    },
    {
      id: 4,
      title: 'Legal AI Assistant',
      description: 'Ask legal questions, get accurate answers with citations — no hallucinations, just facts.',
      icon: MessageSquare,
      path: '/chatbot',
      accent: 'var(--status-ok)',
      tag: 'AI Chat'
    },
    {
      id: 5,
      title: 'Win Probability',
      description: 'Get calibrated success predictions and confidence scores for any case scenario.',
      icon: TrendingUp,
      path: '/outcome',
      accent: 'var(--gold-deep)',
      tag: 'Prediction'
    },
    {
      id: 6,
      title: 'Smart Drafting',
      description: 'Generate court-ready legal documents with automatically embedded precedents and citations.',
      icon: FileText,
      path: '/drafting',
      accent: '#4A6FA5',
      tag: 'Drafting'
    },
    {
      id: 7,
      title: 'Case Analyzer',
      description: 'Upload case details and get instant ML-powered predictions on delay duration and outcome.',
      icon: Gauge,
      path: '/prediction',
      accent: '#6B5B95',
      tag: 'Analysis'
    }
  ];

  const howItWorks = [
    {
      step: '01',
      title: 'Describe Your Case',
      description: 'Enter your case details, upload documents, or simply ask a legal question in plain language.',
      icon: FileText
    },
    {
      step: '02',
      title: 'AI Analyzes & Researches',
      description: 'Our system searches through 10,000+ precedents, identifies risks, and builds a legal strategy.',
      icon: Sparkles
    },
    {
      step: '03',
      title: 'Get Actionable Insights',
      description: 'Receive predictions, risk alerts, timeline estimates, and relevant precedent citations.',
      icon: BarChart3
    },
    {
      step: '04',
      title: 'Draft & Take Action',
      description: 'Generate court-ready documents backed by data, or consult the AI assistant for next steps.',
      icon: CheckCircle2
    }
  ];

  const trustPoints = [
    { value: '10,000+', label: 'Cases Analyzed', icon: BookOpen },
    { value: '92%', label: 'Prediction Accuracy', icon: TrendingUp },
    { value: '< 30s', label: 'Average Response', icon: Zap },
    { value: '6', label: 'AI-Powered Tools', icon: Shield }
  ];

  return (
    <div className="animate-fade-in">
      {/* Status Bar */}
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'flex-end' }}>
        <span className={`badge ${backendStatus === 'connected' ? 'badge-ok' : backendStatus === 'offline' ? 'badge-danger' : 'badge-info'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {backendStatus === 'connected' ? <><Wifi size={10} /> System Online</> : backendStatus === 'offline' ? <><WifiOff size={10} /> Offline</> : '⟳ Connecting...'}
        </span>
      </div>

      {/* Hero */}
      <div style={{ marginBottom: 56, position: 'relative' }}>
        <div style={{
          position: 'absolute',
          top: -40,
          right: -40,
          width: 300,
          height: 300,
          background: 'radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%)',
          borderRadius: '50%',
          pointerEvents: 'none'
        }} />
        <span className="badge badge-gold" style={{ display: 'inline-flex', marginBottom: 16, fontSize: 12 }}>
          ⚖️ AI-Powered Legal Intelligence
        </span>
        <h1 style={{
          fontSize: 48,
          fontWeight: 900,
          fontFamily: 'var(--font-heading)',
          color: 'var(--ink)',
          letterSpacing: '-0.03em',
          lineHeight: 1.08,
          marginBottom: 18,
          maxWidth: 680
        }}>
          Your Legal Research,<br />
          <span style={{
            background: 'linear-gradient(135deg, var(--gold), var(--gold-deep))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            10x Faster.
          </span>
        </h1>
        <p style={{
          fontSize: 18,
          color: 'var(--ink-muted)',
          lineHeight: 1.7,
          maxWidth: 560,
          marginBottom: 28
        }}>
          Search precedents, predict outcomes, detect risks, and draft documents — all in one platform built for the Indian judiciary.
        </p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <Link to="/chatbot" className="btn-gold" style={{ padding: '12px 24px', fontSize: 15 }}>
            <MessageSquare size={17} /> Start Legal Chat
          </Link>
          <Link to="/prediction" className="btn-ink" style={{ background: '#6B5B95', padding: '12px 24px', fontSize: 15 }}>
            <Gauge size={17} /> Analyze a Case
          </Link>
          <Link to="/drafting" className="btn-ghost" style={{ padding: '12px 24px', fontSize: 15 }}>
            <FileText size={17} /> Draft a Document
          </Link>
        </div>
      </div>

      {/* Trust Numbers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: 16,
        marginBottom: 56
      }}>
        {trustPoints.map((point, idx) => {
          const Icon = point.icon;
          return (
            <div key={idx} className={`glass-card animate-fade-in-up stagger-${idx + 1}`} style={{
              padding: '24px 20px',
              textAlign: 'center',
              position: 'relative',
              overflow: 'hidden'
            }}>
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: 3,
                background: 'linear-gradient(90deg, var(--gold), var(--gold-deep))',
                opacity: 0.6
              }} />
              <Icon size={20} color="var(--gold-deep)" style={{ marginBottom: 8 }} />
              <div style={{
                fontSize: 28,
                fontWeight: 900,
                fontFamily: 'var(--font-heading)',
                color: 'var(--ink)',
                letterSpacing: '-0.02em',
                marginBottom: 4
              }}>
                {point.value}
              </div>
              <div style={{
                fontSize: 13,
                color: 'var(--ink-muted)',
                fontWeight: 500
              }}>
                {point.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Feature Modules */}
      <div style={{ marginBottom: 56 }}>
        <div style={{ marginBottom: 24 }}>
          <h2 style={{
            fontSize: 26,
            fontWeight: 800,
            fontFamily: 'var(--font-heading)',
            color: 'var(--ink)',
            letterSpacing: '-0.02em',
            marginBottom: 6
          }}>
            Everything You Need
          </h2>
          <p style={{ fontSize: 15, color: 'var(--ink-muted)', maxWidth: 480 }}>
            Seven powerful tools, one unified platform — designed for lawyers, researchers, and legal teams.
          </p>
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: 16
        }}>
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <Link
                key={feature.id}
                to={feature.path}
                className={`glass-card glass-card-lift animate-fade-in-up stagger-${idx + 1}`}
                style={{
                  padding: 24,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 16,
                  textDecoration: 'none'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{
                    width: 44,
                    height: 44,
                    borderRadius: 'var(--radius-md)',
                    background: `${feature.accent}12`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Icon size={20} color={feature.accent} />
                  </div>
                  <span className="badge badge-gold">{feature.tag}</span>
                </div>
                <div>
                  <h3 style={{
                    fontSize: 17,
                    fontWeight: 700,
                    color: 'var(--ink)',
                    marginBottom: 6,
                    fontFamily: 'var(--font-heading)'
                  }}>
                    {feature.title}
                  </h3>
                  <p style={{
                    fontSize: 13,
                    color: 'var(--ink-muted)',
                    lineHeight: 1.55
                  }}>
                    {feature.description}
                  </p>
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  color: feature.accent,
                  fontWeight: 600,
                  fontSize: 13,
                  marginTop: 'auto'
                }}>
                  <span>Try it now</span>
                  <ArrowRight size={14} />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* How It Works */}
      <div className="glass-card" style={{
        padding: '40px 36px',
        marginBottom: 56,
        background: 'linear-gradient(135deg, rgba(255,255,255,0.9), rgba(245,240,235,0.5))',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          bottom: -60,
          right: -60,
          width: 200,
          height: 200,
          background: 'radial-gradient(circle, rgba(201,168,76,0.06) 0%, transparent 70%)',
          borderRadius: '50%',
          pointerEvents: 'none'
        }} />
        <h2 style={{
          fontSize: 24,
          fontWeight: 800,
          fontFamily: 'var(--font-heading)',
          color: 'var(--ink)',
          marginBottom: 8,
          letterSpacing: '-0.02em'
        }}>
          How It Works
        </h2>
        <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 32, maxWidth: 400 }}>
          From question to court-ready insights in four simple steps.
        </p>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 20
        }}>
          {howItWorks.map((item, idx) => {
            const Icon = item.icon;
            const isActive = idx === activeStep;
            return (
              <div
                key={idx}
                onClick={() => setActiveStep(idx)}
                style={{
                  padding: 24,
                  borderRadius: 'var(--radius-lg)',
                  background: isActive ? 'rgba(201,168,76,0.08)' : 'rgba(255,255,255,0.6)',
                  border: `1.5px solid ${isActive ? 'var(--gold)' : 'var(--border)'}`,
                  cursor: 'pointer',
                  transition: 'all 0.35s ease',
                  transform: isActive ? 'translateY(-2px)' : 'none',
                  boxShadow: isActive ? '0 8px 24px rgba(201,168,76,0.12)' : 'none'
                }}
              >
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  marginBottom: 12
                }}>
                  <div style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--radius-md)',
                    background: isActive ? 'linear-gradient(135deg, var(--gold), var(--gold-deep))' : 'var(--paper-deep)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.35s ease'
                  }}>
                    <Icon size={16} color={isActive ? '#fff' : 'var(--ink-muted)'} />
                  </div>
                  <span style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: isActive ? 'var(--gold-deep)' : 'var(--ink-faint)',
                    fontFamily: 'var(--font-mono)',
                    letterSpacing: '0.08em'
                  }}>
                    STEP {item.step}
                  </span>
                </div>
                <h4 style={{
                  fontSize: 15,
                  fontWeight: 700,
                  color: 'var(--ink)',
                  marginBottom: 6,
                  fontFamily: 'var(--font-heading)'
                }}>
                  {item.title}
                </h4>
                <p style={{
                  fontSize: 13,
                  color: 'var(--ink-muted)',
                  lineHeight: 1.5
                }}>
                  {item.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Social Proof */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: 16,
        marginBottom: 56
      }}>
        {[
          {
            quote: "This tool helped me find a relevant 2019 Supreme Court ruling that completely changed our defense strategy. What would have taken days took under a minute.",
            name: "Adv. Priya Sharma",
            role: "Criminal Defense Lawyer, Delhi HC"
          },
          {
            quote: "The timeline prediction was within 2 months of the actual case duration. The risk analysis caught a contradiction in our filing that we completely missed.",
            name: "Adv. Rajesh Gupta",
            role: "Corporate Litigation, Mumbai"
          },
          {
            quote: "The auto-drafting feature with embedded citations saved our team hours of manual work. It's like having a senior associate who never sleeps.",
            name: "Adv. Meera Patel",
            role: "Legal Researcher, NLU Bangalore"
          }
        ].map((testimonial, idx) => (
          <div key={idx} className={`glass-card animate-fade-in-up stagger-${idx + 1}`} style={{
            padding: 28,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            position: 'relative'
          }}>
            <div style={{
              fontSize: 40,
              lineHeight: 1,
              color: 'var(--gold)',
              fontFamily: 'Georgia, serif',
              opacity: 0.4,
              position: 'absolute',
              top: 16,
              right: 20
            }}>
              "
            </div>
            <p style={{
              fontSize: 14,
              color: 'var(--ink-light)',
              lineHeight: 1.65,
              fontStyle: 'italic',
              flex: 1
            }}>
              "{testimonial.quote}"
            </p>
            <div style={{
              borderTop: '1px solid var(--border)',
              paddingTop: 14,
              display: 'flex',
              alignItems: 'center',
              gap: 12
            }}>
              <div style={{
                width: 38,
                height: 38,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--gold), var(--gold-deep))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 700,
                fontSize: 14,
                fontFamily: 'var(--font-heading)'
              }}>
                {testimonial.name.split(' ').slice(1, 3).map(n => n[0]).join('')}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)' }}>
                  {testimonial.name}
                </div>
                <div style={{ fontSize: 11, color: 'var(--ink-faint)' }}>
                  {testimonial.role}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* CTA Banner */}
      <div style={{
        background: 'linear-gradient(135deg, var(--ink) 0%, #2C2C44 100%)',
        borderRadius: 'var(--radius-xl)',
        padding: '48px 40px',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 24,
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: -40,
          right: -40,
          width: 200,
          height: 200,
          background: 'radial-gradient(circle, rgba(201,168,76,0.15) 0%, transparent 70%)',
          borderRadius: '50%',
          pointerEvents: 'none'
        }} />
        <div style={{
          position: 'absolute',
          bottom: -30,
          left: '30%',
          width: 150,
          height: 150,
          background: 'radial-gradient(circle, rgba(107,91,149,0.1) 0%, transparent 70%)',
          borderRadius: '50%',
          pointerEvents: 'none'
        }} />
        <div style={{ maxWidth: 480, position: 'relative' }}>
          <h2 style={{
            fontSize: 26,
            fontWeight: 800,
            color: '#fff',
            fontFamily: 'var(--font-heading)',
            letterSpacing: '-0.02em',
            marginBottom: 8
          }}>
            Ready to transform your legal practice?
          </h2>
          <p style={{
            fontSize: 15,
            color: 'rgba(255,255,255,0.6)',
            lineHeight: 1.6
          }}>
            Start with a free legal chat or run your first case analysis — see the difference AI can make.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', position: 'relative' }}>
          <Link to="/chatbot" className="btn-gold" style={{ padding: '14px 28px', fontSize: 15 }}>
            <MessageSquare size={17} /> Get Started Free
          </Link>
          <Link to="/precedent-graph" style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '14px 24px',
            color: 'rgba(255,255,255,0.85)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 'var(--radius-md)',
            fontWeight: 600,
            fontSize: 15,
            transition: 'all 0.2s ease',
            background: 'rgba(255,255,255,0.05)'
          }}>
            Explore Tools <ChevronRight size={16} />
          </Link>
        </div>
      </div>
    </div>
  );
}
