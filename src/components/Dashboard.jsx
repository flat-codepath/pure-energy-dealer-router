import React, { useState, useEffect } from 'react';
import { subscribeToLeads } from '../services/leadService.js';
import { countByDealer, countByStatus } from '../services/statsService.js';
import StatusSelect from './StatusSelect.jsx';

export default function Dashboard({ dealers }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Subscribe to live Firestore updates on mount
  useEffect(() => {
    setLoading(true);
    const unsubscribe = subscribeToLeads(
      updatedLeads => {
        setLeads(updatedLeads);
        setLoading(false);
      },
      err => {
        setError('Failed to load live leads: ' + err.message);
        setLoading(false);
      }
    );

    // Clean up onSnapshot listener when component unmounts
    return () => unsubscribe();
  }, []);

  // Compute live aggregates using pure functions from statsService
  const dealerCounts = countByDealer(leads, dealers);
  const statusCounts = countByStatus(leads);

  // Formats Firestore Timestamp or Date object safely
  function formatCreatedAt(timestamp) {
    if (!timestamp) return 'Just now';
    if (typeof timestamp.toDate === 'function') {
      return timestamp.toDate().toLocaleString('en-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    }
    if (timestamp instanceof Date) {
      return timestamp.toLocaleString('en-IN');
    }
    return String(timestamp);
  }

  return (
    <div className="dashboard-container">
      {/* Summary Analytics Section */}
      <section className="summary-section">
        <h2>Live Summary</h2>

        <div className="summary-grid">
          {/* Summary Table: Lead Count by Status */}
          <div className="card summary-card">
            <h3>Leads by Status</h3>
            <p className="card-subtitle">All canonical statuses tracked</p>
            <table className="data-table summary-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th className="text-right">Count</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(statusCounts).map(([status, count]) => (
                  <tr key={status}>
                    <td>
                      <span className={`status-pill status-${status.toLowerCase()}`}>
                        {status}
                      </span>
                    </td>
                    <td className="text-right font-semibold">{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary Table: Lead Count by Dealer */}
          <div className="card summary-card">
            <h3>Leads by Dealer / Channel</h3>
            <p className="card-subtitle">Including In-house Sales fallback</p>
            <table className="data-table summary-table">
              <thead>
                <tr>
                  <th>Dealer / Channel</th>
                  <th className="text-right">Count</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(dealerCounts).map(([dealerName, count]) => (
                  <tr key={dealerName}>
                    <td>{dealerName}</td>
                    <td className="text-right font-semibold">{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Main Leads Table Section */}
      <section className="leads-section card">
        <div className="section-header">
          <div>
            <h2>All Routed Leads</h2>
            <p className="card-subtitle">
              Live updates powered by Firestore onSnapshot ({leads.length} total)
            </p>
          </div>
        </div>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        {loading ? (
          <div className="loading-state">Loading leads from Firestore...</div>
        ) : leads.length === 0 ? (
          <div className="empty-state">
            <p>No leads found in database.</p>
            <p className="empty-state-hint">Use the form above to submit your first lead.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table leads-table">
              <thead>
                <tr>
                  <th>Customer Name</th>
                  <th>Mobile</th>
                  <th>Pincode</th>
                  <th>Product</th>
                  <th>Source</th>
                  <th>Assigned Dealer</th>
                  <th>Created Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {leads.map(lead => (
                  <tr key={lead.id || lead.mobile}>
                    <td className="font-medium">{lead.name}</td>
                    <td>{lead.mobile}</td>
                    <td><code>{lead.pincode}</code></td>
                    <td>{lead.product}</td>
                    <td>
                      <span className="source-tag">{lead.source}</span>
                    </td>
                    <td>
                      <span className="dealer-tag font-medium">{lead.dealer}</span>
                    </td>
                    <td className="text-muted">{formatCreatedAt(lead.createdAt)}</td>
                    <td>
                      <StatusSelect
                        mobile={lead.mobile}
                        currentStatus={lead.status}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
