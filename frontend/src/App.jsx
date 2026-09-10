// src/App.jsx
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChartsGrid } from './components/ChartsGrid';
import { gridStyles } from './components/chartStyles';
import { CustomerDrawer } from './components/CustomerDrawer';
import { CustomerRegistry } from './components/CustomerRegistry';
import { CustomerRiskScoreHistoryChart } from './components/CustomerRiskScoreHistoryChart';
import { CustomerScoreHistoryChart } from './components/CustomerScoreHistoryChart';
import { CustomerSidebar } from './components/CustomerSidebar';
import { ExceptionQueue } from './components/ExceptionQueue';
import { KPICards } from './components/KPICards';
import { Navbar } from './components/Navbar';
import { PolicyReference } from './components/PolicyReference';

const API_BASE = 'http://localhost:8000';

// Reads the initial selection from the URL so a refresh keeps the same customer
// in view instead of dropping back to the portfolio.
const readCustomerFromUrl = () => {
  const raw = new URLSearchParams(window.location.search).get('customer');
  const id = raw ? Number(raw) : null;
  return Number.isFinite(id) && id > 0 ? id : null;
};

function App() {
  const [customers, setCustomers] = useState([]);
  const [kpis, setKpis] = useState({});
  // The single source of truth for "which customer is the dashboard showing."
  // Every entry point - the sidebar, the header search, and the registry's
  // "Open Profile" - sets this and nothing else. null means the portfolio view.
  const [selectedCustomerId, setSelectedCustomerId] = useState(readCustomerFromUrl);
  // The full committee report is now a separate, explicit destination reached
  // via "Open full report" in the customer view; selecting alone no longer opens it.
  const [openReportId, setOpenReportId] = useState(null);
  // The registry is a third trigger onto the same selection; it stays mounted
  // behind the workspace so closing it returns the underwriter to their place.
  const [registryOpen, setRegistryOpen] = useState(false);
  const [registryLoaded, setRegistryLoaded] = useState(false);
  const [error, setError] = useState(null);
  // Bumped whenever a write lands (audit run, underwriter override) so the
  // aggregate views refetch instead of showing pre-write numbers.
  const [dataVersion, setDataVersion] = useState(0);

  useEffect(() => {
    // The registry endpoint is a superset of /customers: same roster, plus each
    // client's standing verdict and whether a saved audit exists. One fetch feeds
    // the navbar search badges, the sidebar, and the registry table.
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

  // Mirrors the selection into the URL without pulling in a router.
  useEffect(() => {
    const url = new URL(window.location.href);
    if (selectedCustomerId != null) {
      url.searchParams.set('customer', String(selectedCustomerId));
    } else {
      url.searchParams.delete('customer');
    }
    window.history.replaceState({}, '', url);
  }, [selectedCustomerId]);

  const selectCustomer = useCallback((customerId) => {
    setSelectedCustomerId(customerId);
    setRegistryOpen(false);
  }, []);
  const clearSelection = useCallback(() => setSelectedCustomerId(null), []);
  const handleDataChange = useCallback(() => setDataVersion((v) => v + 1), []);

  // Esc returns to the portfolio view - but only when the registry modal isn't
  // already claiming Esc for itself.
  useEffect(() => {
    if (registryOpen || selectedCustomerId == null) return;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') clearSelection();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [registryOpen, selectedCustomerId, clearSelection]);

  const avgScore = customers.length
    ? Math.round(customers.reduce((sum, c) => sum + c.credit_score, 0) / customers.length)
    : 0;

  const selectedCustomer = useMemo(
    () => customers.find((c) => c.customer_id === selectedCustomerId) ?? null,
    [customers, selectedCustomerId],
  );

  const listLoading = !registryLoaded && !error;

  return (
    <div style={appStyles.shell}>
      <Navbar customers={customers} onSelectCustomer={selectCustomer} />

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
        loading={listLoading}
        error={error}
        onClose={() => setRegistryOpen(false)}
        onInspectCustomer={selectCustomer}
      />

      <div style={appStyles.workspace}>
        <CustomerSidebar
          customers={customers}
          loading={listLoading}
          error={error}
          selectedCustomerId={selectedCustomerId}
          onSelect={selectCustomer}
          onClear={clearSelection}
        />

        <div style={appStyles.main}>
          {selectedCustomer ? (
            <CustomerView
              customer={selectedCustomer}
              refreshKey={dataVersion}
              onOpenReport={() => setOpenReportId(selectedCustomer.customer_id)}
              onClear={clearSelection}
            />
          ) : (
            <ChartsGrid customers={customers} refreshKey={dataVersion} />
          )}
        </div>
      </div>

      <PolicyReference />

      <ExceptionQueue
        refreshKey={dataVersion}
        onInspectCustomer={selectCustomer}
        onDecisionRecorded={handleDataChange}
      />

      {/* Keyed by client: remounting gives each customer a clean audit-poll
          state, so no stale progress survives a switch. */}
      <CustomerDrawer
        key={openReportId}
        customerId={openReportId}
        onClose={() => setOpenReportId(null)}
        onAuditComplete={handleDataChange}
      />
    </div>
  );
}

// Phase 1 stand-in for the full applicant card (built in Phase 2): proves the
// portfolio/customer view switch and reuses the two history charts, which
// already work per-customer without any new backend surface.
function CustomerView({ customer, refreshKey, onOpenReport, onClear }) {
  return (
    <div style={appStyles.customerView}>
      <div style={appStyles.customerHead}>
        <div>
          <h2 style={appStyles.customerName}>{customer.full_name}</h2>
          <span style={appStyles.customerMeta}>
            #{customer.customer_id} · Credit score {customer.credit_score} ·{' '}
            {customer.has_saved_audit ? customer.decision_status : 'Not analyzed'}
          </span>
        </div>
        <div style={appStyles.customerActions}>
          <button type="button" style={appStyles.reportBtn} onClick={onOpenReport}>
            Open full report
          </button>
          <button type="button" style={appStyles.backBtn} onClick={onClear}>
            ← Back to portfolio
          </button>
        </div>
      </div>

      <div style={gridStyles.container}>
        <CustomerScoreHistoryChart customerId={customer.customer_id} refreshKey={refreshKey} />
        <CustomerRiskScoreHistoryChart customerId={customer.customer_id} refreshKey={refreshKey} />
      </div>
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
  workspace: {
    display: 'grid',
    gridTemplateColumns: 'minmax(240px, 280px) 1fr',
    gap: '20px',
    alignItems: 'start',
    marginBottom: '24px',
  },
  main: { minWidth: 0 },
  customerView: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '20px',
  },
  customerHead: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: '12px',
    marginBottom: '16px',
    paddingBottom: '14px',
    borderBottom: '1px solid var(--border)',
  },
  customerName: { margin: 0, fontSize: '18px', color: 'var(--text-primary)' },
  customerMeta: { fontSize: '12px', color: 'var(--text-secondary)' },
  customerActions: { display: 'flex', gap: '8px', flexWrap: 'wrap' },
  reportBtn: {
    background: 'var(--accent)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 14px',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  backBtn: {
    background: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    padding: '8px 14px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
};

export default App;
