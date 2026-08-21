import React, { useState, useEffect } from 'react';
import { fetchCustomers, fetchCustomerProfile, runRiskAudit } from './services/api';

function App() {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [profile, setProfile] = useState(null);
  const [auditResult, setAuditResult] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [error, setError] = useState(null);

  // 1. Fetch customer list on load
  useEffect(() => {
    fetchCustomers()
      .then((data) => {
        setCustomers(data);
        if (data.length > 0) {
          setSelectedCustomerId(data[0].customer_id);
        }
      })
      .catch(() => setError("Failed to load customer list. Make sure FastAPI backend is running."));
  }, []);

  // 2. Fetch selected customer profile details
  useEffect(() => {
    if (!selectedCustomerId) return;
    
    setLoadingProfile(true);
    setAuditResult(null); // Reset audit view when switching customers
    setError(null);

    fetchCustomerProfile(selectedCustomerId)
      .then((data) => setProfile(data))
      .catch(() => setError("Failed to fetch customer profile metrics."))
      .finally(() => setLoadingProfile(false));
  }, [selectedCustomerId]);

  // 3. Trigger Multi-Agent Risk Audit
  const handleRunAudit = () => {
    setLoadingAudit(true);
    setError(null);

    runRiskAudit(selectedCustomerId)
      .then((data) => setAuditResult(data))
      .catch(() => setError("Audit failed to execute. Check backend logs."))
      .finally(() => setLoadingAudit(false));
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, -apple-system, sans-serif', maxWidth: '1000px', margin: '0 auto' }}>
      <h1>Financial Risk AI Dashboard</h1>
      
      {error && (
        <div style={{ background: '#fee2e2', color: '#991b1b', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* Customer Selector Dropdown */}
      <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#f9fafb' }}>
        <label style={{ fontWeight: 'bold', marginRight: '1rem' }}>Select Customer:</label>
        <select 
          value={selectedCustomerId} 
          onChange={(e) => setSelectedCustomerId(e.target.value)}
          style={{ padding: '0.5rem 1rem', fontSize: '1rem', borderRadius: '6px' }}
        >
          {customers.map((c) => (
            <option key={c.customer_id} value={c.customer_id}>
              {c.full_name} (ID: {c.customer_id})
            </option>
          ))}
        </select>
      </div>

      {loadingProfile ? (
        <p>Loading customer profile...</p>
      ) : profile && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {/* Financial Profile Card */}
          <div style={{ border: '1px solid #e5e7eb', padding: '1.5rem', borderRadius: '8px', background: '#ffffff' }}>
            <h2>Customer Profile</h2>
            <p><strong>Name:</strong> {profile.full_name}</p>
            <p><strong>Credit Score:</strong> {profile.credit_score}</p>
            <p><strong>DTI Ratio:</strong> {(profile.debt_to_income_ratio * 100).toFixed(1)}%</p>
            <p><strong>Annual Income:</strong> ${profile.annual_income.toLocaleString()}</p>
            <p><strong>Requested Loan:</strong> ${profile.loan_amount_requested.toLocaleString()}</p>
            <p><strong>XGBoost Default Risk:</strong> {(profile.live_xgb_risk_score * 100).toFixed(2)}%</p>
            <p><strong>Sanitized CPF:</strong> {profile.cpf || 'N/A'}</p>

            <button 
              onClick={handleRunAudit}
              disabled={loadingAudit}
              style={{
                marginTop: '1rem',
                width: '100%',
                padding: '0.75rem',
                backgroundColor: loadingAudit ? '#9ca3af' : '#2563eb',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '1rem',
                cursor: loadingAudit ? 'not-allowed' : 'pointer'
              }}
            >
              {loadingAudit ? "Multi-Agent Committee Auditing..." : "Run Risk Audit"}
            </button>
          </div>

          {/* Audit Results Card */}
          <div style={{ border: '1px solid #e5e7eb', padding: '1.5rem', borderRadius: '8px', background: '#f8fafc' }}>
            <h2>Audit Committee Decision</h2>
            {auditResult ? (
              <div>
                <p><strong>Standing:</strong> <span style={{ color: auditResult.quantitative_standing === 'LOW RISK' ? 'green' : 'orange' }}>{auditResult.quantitative_standing}</span></p>
                <p><strong>CRO Executive Decision:</strong></p>
                <blockquote style={{ background: '#e2e8f0', padding: '1rem', borderRadius: '6px', fontStyle: 'italic' }}>
                  {auditResult.cro_decision || "Decision completed."}
                </blockquote>
              </div>
            ) : (
              <p style={{ color: '#64748b' }}>Click "Run Risk Audit" to evaluate this customer through the AI pipeline.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
