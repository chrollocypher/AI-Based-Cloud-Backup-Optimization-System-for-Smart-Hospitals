import { ExternalLink, RefreshCw } from 'lucide-react';
import { API_BASE, DOCS_URL, api } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { ErrorBox, Loading, PageHeader, Panel } from '../components/ui.jsx';
import { fmtDateTime, timeAgo } from '../lib/format.js';

function Row({ label, ok, value }) {
  return (
    <div className="sys-row">
      <span>{label}</span>
      {ok !== undefined ? (
        <span className={ok ? 'status status-completed' : 'status status-failed'}>
          <i aria-hidden="true" />
          {ok ? 'Active' : 'Down'}
        </span>
      ) : (
        <span>{value}</span>
      )}
    </div>
  );
}

export default function System() {
  const monitoring = useApi(api.monitoring, [], { interval: 15000 });
  const health = useApi(api.health, [], { interval: 15000 });

  const refresh = () => {
    monitoring.reload(true);
    health.reload(true);
  };

  if ((monitoring.error && !monitoring.data) || (health.error && !health.data)) {
    return <ErrorBox error={monitoring.error || health.error} onRetry={refresh} />;
  }
  if (!monitoring.data || !health.data) return <Loading label="Checking system" />;

  const m = monitoring.data;
  const h = health.data;

  return (
    <>
      <PageHeader
        title="System"
        subtitle={h.service}
        actions={
          <>
            <a className="btn" href={DOCS_URL} target="_blank" rel="noreferrer">
              <ExternalLink size={16} aria-hidden="true" />
              API docs
            </a>
            <button className="btn" onClick={refresh}>
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </button>
          </>
        }
      />
      <div className="two-col">
        <Panel title="Components" subtitle={`Overall status: ${m.system_status.toLowerCase()}`}>
          <Row label="Database" ok={m.database_connected} />
          <Row label="AWS services" ok={m.aws_services_active} />
          <Row label="Scheduler" ok={m.active_scheduler} />
          <Row label="Running backup jobs" value={m.active_jobs_count} />
          <Row label="Last forecast" value={`${timeAgo(m.last_prediction_time)} (${fmtDateTime(m.last_prediction_time)})`} />
        </Panel>
        <Panel title="Environment">
          <Row label="Environment" value={h.environment} />
          <Row label="AWS mode" value={h.use_mock_aws ? 'Mock (no real AWS calls)' : 'Live'} />
          <Row label="API base URL" value={<span className="path wrap">{API_BASE}</span>} />
        </Panel>
      </div>
    </>
  );
}
