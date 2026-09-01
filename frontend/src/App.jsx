// src/App.jsx
import { useCallback, useEffect, useState } from 'react';
import { ChartsGrid } from './components/ChartsGrid';
import { CustomerDrawer } from './components/CustomerDrawer';
import { CustomerRegistry } from './components/CustomerRegistry';
import { ExceptionQueue } from './components/ExceptionQueue';
import { KPICards } from './components/KPICards';
import { Navbar } from './components/Navbar';
import { PolicyReference } from './components/PolicyReference';

const API_BASE = 'http://localhost:8000';

function App() {
  const [customers, setCustomers] = useState([]);
  const [kpis, setKpis] = useState({});
  // A single source of truth: null means no client is open. The navbar quick
  // search and the exception queue are two triggers onto the same drawer.
  const [inspectedId, setInspectedId] = useState(null);
  // The registry is a third trigger onto the same drawer; it stays mounted behind
  // the drawer so closing a report returns the underwriter to their place in the list.
  const [registryOpen, setRegistryOpen] = useState(false);
  const [registryLoaded, setRegistryLoaded] = useState(false);
  const [error, setError] = useState(null);
  // Bumped whenever a write lands (audit run, underwriter override) so the
  // aggregate views refetch instead of showing pre-write numbers.
  const [dataVersion, setDataVersion] = useState(0);

  useEffect(() => {
    // The registry endpoint is a superset of /customers: same roster, plus each
    // client's standing verdict and whether a saved audit exists. One fetch feeds
    // the navbar search badges, the score histogram, and the registry table.
    fetch(`${API_BASE}/api/dashboard/customer-registry`)
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/dashboard/customer-registry -> ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setCustomers(Array.isArray(data) ? data : []);
        setRegistryLoaded(true);
      })
      .catch((err) => setError(err.message));

    fetch(`${API_BASE}/api/dashboard/kpis`)
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/dashboard/kpis -> ${res.status}`);
        return res.json();
      })
      .then(setKpis)
      .catch((err) => setError(err.message));
  }, [dataVersion]);

  const handleInspect = useCallback((customerId) => setInspectedId(customerId), []);
  const handleDataChange = useCallback(() => setDataVersion((v) => v + 1), []);

  const avgScore = customers.length
    ? Math.round(customers.reduce((sum, c) => sum + c.credit_score, 0) / customers.length)
    : 0;

  return (
    <div style={appStyles.shell}>
      <Navbar customers={customers} onSelectCustomer={handleInspect} />

      {error && (
        <div style={appStyles.error}>
          Backend unreachable: {error}. Start the API with{' '}
          <code>uvicorn src.api.main:app --reload</code>
        </div>
      )}

      <KPICards
        kpis={{
          total: kpis.total_customers,
          analyzed: kpis.analyzed_customers,
          totalApplications: kpis.total_applications,
          avgScore,
          approvalRate: kpis.approval_rate_pct,
          avgTime: kpis.avg_decision_time_sec,
        }}
        onViewAllCustomers={() => setRegistryOpen(true)}
      />

      <CustomerRegistry
        open={registryOpen}
        customers={customers}
        loading={!registryLoaded && !error}
        error={error}
        onClose={() => setRegistryOpen(false)}
        onInspectCustomer={handleInspect}
      />

      <ChartsGrid customers={customers} refreshKey={dataVersion} />

      <PolicyReference />

      <ExceptionQueue
        refreshKey={dataVersion}
        onInspectCustomer={handleInspect}
        onDecisionRecorded={handleDataChange}
      />

      {/* Keyed by client: remounting gives each customer a clean profile/audit
          state, so no stale demographics survive a switch. */}
      <CustomerDrawer
        key={inspectedId}
        customerId={inspectedId}
        onClose={() => setInspectedId(null)}
        onAuditComplete={handleDataChange}
      />
    </div>
  );
}

const appStyles = {
  shell: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '24px',
    minHeight: '100vh',
  },
  error: {
    background: 'var(--surface)',
    border: '1px solid var(--status-rejected)',
    color: 'var(--status-rejected)',
    borderRadius: '8px',
    padding: '12px 16px',
    marginBottom: '20px',
    fontSize: '13px',
  },
};

export default App;
