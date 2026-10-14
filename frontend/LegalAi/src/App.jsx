import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import { Menu } from 'lucide-react';

import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import CaseWorkspace from './pages/CaseWorkspace';
import PrecedentGraph from './pages/PrecedentGraph';
import ContradictionDetector from './pages/ContradictionDetector';
import ChatBot from './pages/ChatBot';
import AutoDrafting from './pages/AutoDrafting';
import CasePrediction from './pages/CasePrediction';
import Dictation from './pages/Dictation';
import Chronology from './pages/Chronology';
import CourtDocket from './pages/CourtDocket';
import ClientPortal from './pages/ClientPortal';
import Analytics from './pages/Analytics';

import './App.css';

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <Router>
      <Sidebar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      <main className={`main-content ${collapsed ? 'sidebar-collapsed' : ''}`}>
        {/* Mobile top bar */}
        <div className="md:hidden" style={{
          position: 'sticky',
          top: 0,
          zIndex: 30,
          padding: '12px 16px',
          background: 'var(--paper)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 12
        }}>
          <button
            onClick={() => setMobileOpen(true)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--ink)',
              padding: 4,
              cursor: 'pointer'
            }}
          >
            <Menu size={22} />
          </button>
          <span style={{
            fontFamily: 'var(--font-heading)',
            fontWeight: 700,
            fontSize: 16,
            color: 'var(--ink)'
          }}>
            Nyay AI
          </span>
        </div>

        <div style={{ padding: '32px 40px', maxWidth: 1280, margin: '0 auto' }}>
          <Routes>
            <Route path="/" element={<CaseWorkspace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/precedent-graph" element={<PrecedentGraph />} />
            <Route path="/contradiction" element={<ContradictionDetector />} />
            <Route path="/chatbot" element={<ChatBot />} />
            <Route path="/prediction" element={<CasePrediction />} />
            <Route path="/drafting" element={<AutoDrafting />} />
            <Route path="/dictation" element={<Dictation />} />
            <Route path="/chronology" element={<Chronology />} />
            <Route path="/court-docket" element={<CourtDocket />} />
            <Route path="/client-portal" element={<ClientPortal />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </div>

        {/* Footer */}
        <footer style={{
          padding: '20px 40px',
          borderTop: '1px solid var(--border)',
          textAlign: 'center',
          fontSize: 12,
          color: 'var(--ink-faint)'
        }}>
          <p>Nyay AI — Indian Legal Intelligence System &middot; For informational purposes only &middot; Consult a qualified attorney for legal advice</p>
        </footer>
      </main>
    </Router>
  );
}

export default App;
