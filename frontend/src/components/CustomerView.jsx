// src/components/CustomerView.jsx
import { useCommitteeAudit } from '../hooks/useCommitteeAudit';
import { useCustomerProfile } from '../hooks/useCustomerProfile';
import { AgentRecommendations } from './AgentRecommendations';
import { ApplicantCard } from './ApplicantCard';
import { gridStyles } from './chartStyles';
import { CustomerRiskScoreHistoryChart } from './CustomerRiskScoreHistoryChart';
import { CustomerScoreHistoryChart } from './CustomerScoreHistoryChart';
import { CustomerVsPortfolio } from './CustomerVsPortfolio';

// The main area once a customer is selected: the applicant card (same fields
// the profile drawer shows, plus the audit trigger), the two history charts,
// a portfolio comparison, and the agent recommendations panel. "Open full
// report" is the only path to the full transcript drawer.
export function CustomerView({ customerId, refreshKey, onAuditComplete, onOpenReport, onClear }) {
  const { profile, error: profileError } = useCustomerProfile(customerId);
  const audit = useCommitteeAudit(customerId, onAuditComplete);

  return (
    <div style={viewStyles.wrap}>
      <ApplicantCard
        profile={profile}
        error={profileError}
        audit={audit}
        onOpenReport={onOpenReport}
        onClear={onClear}
      />

      <div style={gridStyles.container}>
        <CustomerScoreHistoryChart customerId={customerId} refreshKey={refreshKey} />
        <CustomerRiskScoreHistoryChart customerId={customerId} refreshKey={refreshKey} />
        {profile && <CustomerVsPortfolio profile={profile} refreshKey={refreshKey} />}
        <AgentRecommendations audit={audit} />
      </div>
    </div>
  );
}

const viewStyles = {
  wrap: { display: 'flex', flexDirection: 'column', gap: '20px' },
};
