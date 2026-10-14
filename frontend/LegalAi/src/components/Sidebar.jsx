import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, Bell, CalendarDays, ChevronLeft, ChevronRight, FileSignature, FileText, Gauge, Mic, Plus, Scale } from 'lucide-react';

export default function Sidebar({ collapsed, setCollapsed, mobileOpen, setMobileOpen }) {
  const [savedCases, setSavedCases] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const loadSavedCase = () => {
      try {
        const value = localStorage.getItem('legalai_active_case');
        const activeCase = value ? JSON.parse(value) : null;
        const cases = JSON.parse(localStorage.getItem('legalai_cases') || '[]');
        const uniqueCases = [...(cases.length ? cases : activeCase ? [activeCase] : [])].reduce((result, item) => {
          const key = item.caseText || `${item.title}|${(item.files || []).join('|')}`;
          if (!result.some((existing) => (existing.caseText || `${existing.title}|${(existing.files || []).join('|')}`) === key)) {
            result.push(item);
          }
          return result;
        }, []).slice(0, 20);
        localStorage.setItem('legalai_cases', JSON.stringify(uniqueCases));
        setSavedCases(uniqueCases);
      } catch {
        setSavedCases([]);
      }
    };

    loadSavedCase();
    window.addEventListener('legalai-case-saved', loadSavedCase);
    return () => window.removeEventListener('legalai-case-saved', loadSavedCase);
  }, []);

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="mobile-overlay md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        {/* Brand */}
        <div style={{
          padding: collapsed ? '20px 0' : '20px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          justifyContent: collapsed ? 'center' : 'flex-start',
          minHeight: '72px'
        }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, var(--gold), var(--gold-deep))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <Scale size={18} color="#fff" />
          </div>
          {!collapsed && (
            <div className="animate-fade-in">
              <div style={{ fontSize: 18, fontWeight: 800, fontFamily: 'var(--font-heading)', color: '#fff', letterSpacing: '-0.02em' }}>
                Nyay AI
              </div>
              <div style={{ fontSize: 10, color: 'var(--ink-subtle)', fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Judiciary Intelligence
              </div>
            </div>
          )}
        </div>

        {/* Workflow navigation and case history */}
        <div className="case-history-nav">
          <Link className="history-tool-button" to="/prediction" onClick={() => setMobileOpen(false)} title="Open Case Prediction">
            <Gauge size={16} />
            {!collapsed && <span>Case Prediction</span>}
          </Link>
          <Link className="history-tool-button" to="/drafting" onClick={() => setMobileOpen(false)} title="Open Auto Drafting">
            <FileText size={16} />
            {!collapsed && <span>Auto Drafting</span>}
          </Link>
          <Link className="history-tool-button" to="/dictation" onClick={() => setMobileOpen(false)} title="Open Legal Dictation">
            <Mic size={16} />
            {!collapsed && <span>Legal Dictation</span>}
          </Link>
          <Link className="history-tool-button" to="/chronology" onClick={() => setMobileOpen(false)} title="Open Evidence Chronology">
            <CalendarDays size={16} />
            {!collapsed && <span>Evidence Chronology</span>}
          </Link>
          <Link className="history-tool-button" to="/court-docket" onClick={() => setMobileOpen(false)} title="Open Court Docket Tracker">
            <Bell size={16} />
            {!collapsed && <span>Court Docket Tracker</span>}
          </Link>
          <Link className="history-tool-button" to="/client-portal" onClick={() => setMobileOpen(false)} title="Open Client Portal">
            <FileSignature size={16} />
            {!collapsed && <span>Client Portal</span>}
          </Link>
          <Link className="history-tool-button" to="/analytics" onClick={() => setMobileOpen(false)} title="Open Case Analytics">
            <BarChart3 size={16} />
            {!collapsed && <span>Case Analytics</span>}
          </Link>

          {!collapsed && <div className="case-history-label">Case history</div>}
          <Link
            className="history-new-case"
            to="/?new=1"
            onClick={(event) => {
              event.preventDefault();
              setMobileOpen(false);
              navigate(`/?new=1&fresh=${Date.now()}`);
            }}
            title="Create a new case"
          >
            <Plus size={16} />
            {!collapsed && <span>New case</span>}
          </Link>
          <div className="history-list">
            {savedCases.length ? savedCases.map((savedCase) => (
              <Link key={savedCase.id} className="history-case" to={`/?case=${encodeURIComponent(savedCase.id)}`} onClick={() => setMobileOpen(false)} title={savedCase.title}>
                <Scale size={15} />
                {!collapsed && <span><strong>{savedCase.title}</strong><small>{new Date(savedCase.updatedAt).toLocaleDateString()}</small></span>}
              </Link>
            )) : !collapsed && <div className="history-empty">No saved cases yet</div>}
          </div>
        </div>

        {/* Collapse toggle (desktop only) */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden md:flex"
          style={{
            padding: '14px',
            background: 'none',
            border: 'none',
            borderTop: '1px solid rgba(255,255,255,0.08)',
            color: 'var(--ink-subtle)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-end',
            gap: '8px',
            fontSize: '12px',
            transition: 'color 0.2s ease'
          }}
          onMouseEnter={e => e.currentTarget.style.color = '#fff'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--ink-subtle)'}
        >
          {collapsed ? <ChevronRight size={16} /> : (
            <>
              <span>Collapse</span>
              <ChevronLeft size={16} />
            </>
          )}
        </button>
      </aside>
    </>
  );
}
