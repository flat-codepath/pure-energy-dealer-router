import React, { useState, useEffect } from 'react';
import { getDealers } from './services/dealerService.js';
import LeadForm from './components/LeadForm.jsx';
import Dashboard from './components/Dashboard.jsx';

export default function App() {
  const [dealers, setDealers] = useState([]);
  const [loadingDealers, setLoadingDealers] = useState(true);
  const [dealerError, setDealerError] = useState(null);

  // Load dealers once on application mount and reuse throughout session
  useEffect(() => {
    async function loadDealers() {
      try {
        setLoadingDealers(true);
        const data = await getDealers();
        setDealers(data);
      } catch (err) {
        console.error('Failed to load dealers from Firestore:', err);
        setDealerError('Could not load dealers directory. Pincodes will route to In-house Sales.');
      } finally {
        setLoadingDealers(false);
      }
    }

    loadDealers();
  }, []);

  return (
    <div className="app-container">
      {/* Top Application Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="logo-badge">⚡ PuRE</div>
          <div>
            <h1>Dealer Lead Router</h1>
            <p className="header-subtitle">MIS Assistant Territory Routing & Management</p>
          </div>
        </div>
        <div className="header-meta">
          <span className="badge">
            {loadingDealers ? 'Loading dealers...' : `${dealers.length} Active Dealers`}
          </span>
        </div>
      </header>

      {dealerError && (
        <div className="alert alert-warning" role="alert">
          {dealerError}
        </div>
      )}

      {/* Main Content Layout */}
      <main className="main-content">
        {/* Lead Capture Form */}
        <section className="form-section">
          <LeadForm dealers={dealers} />
        </section>

        {/* Live Dashboard (Leads Table & Aggregates) */}
        <section className="dashboard-section">
          <Dashboard dealers={dealers} />
        </section>
      </main>

      {/* Application Footer */}
      <footer className="app-footer">
        <p>PURE Energy — Dealer Lead Router &copy; {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}
