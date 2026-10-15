import { useState } from 'react';
import { ExternalLink, RefreshCw, Send, Workflow } from 'lucide-react';
import { API_BASE, DOCS_URL, api } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { DefinitionList, Drawer, Empty, ErrorBox, Loading, PageHeader, Panel, useToast } from '../components/ui.jsx';
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

const EXEC_STATUS = {
  SUCCEEDED: 'badge-success',
  RUNNING: 'badge-neutral',
  FAILED: 'badge-danger',
};

export default function System() {
  const toast = useToast();
  const monitoring = useApi(api.monitoring, [], { interval: 15000 });
  const health = useApi(api.health, [], { interval: 15000 });
  const executions = useApi(api.listPipelineExecutions, [], { interval: 15000 });

  const [publishing, setPublishing] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const refresh = () => {
    monitoring.reload(true);
    health.reload(true);
    executions.reload(true);
  };

  const publish = async () => {
    setPublishing(true);
    try {
      const res = await api.publishCloudWatch();
      toast.success(`Published ${res.metric_count} metrics to ${res.namespace} (${res.mode}).`);
    } catch (e) {
      toast.error(`Publish failed: ${e.message}`);
    } finally {
      setPublishing(false);
    }
  };

  const openExecution = async (id) => {
    setSelected(id);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      setDetail(await api.getExecution(id));
    } catch (e) {
      setDetailError(e);
    } finally {
      setDetailLoading(false);
    }
  };

  const rows = [...(executions.data || [])].sort((a, b) => new Date(b.started_at) - new Date(a.started_at));

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
            <button className="btn" onClick={publish} disabled={publishing}>
              <Send size={16} aria-hidden="true" />
              {publishing ? 'Publishing' : 'Publish metrics'}
            </button>
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

      <Panel
        title="Storage pipeline executions"
        subtitle="AWS Step Functions runs triggered from the Storage & Retrieval page"
        flush
      >
        {executions.error && !executions.data ? (
          <ErrorBox error={executions.error} onRetry={executions.reload} />
        ) : !executions.data ? (
          <Loading label="Loading executions" />
        ) : rows.length === 0 ? (
          <Empty title="No pipeline executions yet">
            Trigger the storage optimization pipeline from the Storage &amp; Retrieval page.
          </Empty>
        ) : (
          <div className="table-wrap">
            <table className="table clickable">
              <thead>
                <tr>
                  <th>Execution</th>
                  <th>Status</th>
                  <th>Intensity</th>
                  <th className="num">Transitions</th>
                  <th>Mode</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((ex) => (
                  <tr
                    key={ex.execution_id}
                    tabIndex={0}
                    onClick={() => openExecution(ex.execution_id)}
                    onKeyDown={(e) => e.key === 'Enter' && openExecution(ex.execution_id)}
                  >
                    <td><div className="cell-strong">{ex.execution_id}</div></td>
                    <td>
                      <span className={`badge ${EXEC_STATUS[ex.status] || 'badge-neutral'}`}>{ex.status}</span>
                    </td>
                    <td>{ex.forecast_intensity || '—'}</td>
                    <td className="num">{ex.transitions_executed ?? '—'}</td>
                    <td>{ex.mode}</td>
                    <td>{fmtDateTime(ex.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Drawer
        open={!!selected}
        title={selected || ''}
        onClose={() => setSelected(null)}
      >
        {detailLoading ? (
          <Loading label="Loading execution" />
        ) : detailError ? (
          <ErrorBox error={detailError} onRetry={() => openExecution(selected)} />
        ) : detail ? (
          <>
            <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
              <Workflow size={18} aria-hidden="true" />
              <span className={`badge ${EXEC_STATUS[detail.status] || 'badge-neutral'}`}>{detail.status}</span>
              <span className="badge badge-neutral">{detail.mode}</span>
            </div>
            <DefinitionList
              items={[
                ['Execution ID', detail.execution_id],
                ['Started', fmtDateTime(detail.started_at)],
                ['Completed', detail.completed_at ? fmtDateTime(detail.completed_at) : '—'],
                ['Forecast intensity', detail.forecast_intensity || '—'],
                ['Transitions executed', detail.transitions_executed ?? '—'],
                ['Execution ARN', <span className="path wrap" key="arn">{detail.executionArn || '—'}</span>],
              ]}
            />
            {detail.output && (
              <>
                <h3 className="small muted">State machine output</h3>
                <pre className="soft-box mono" style={{ margin: 0, maxHeight: '320px', overflow: 'auto' }}>
                  {JSON.stringify(detail.output, null, 2)}
                </pre>
              </>
            )}
          </>
        ) : null}
      </Drawer>
    </>
  );
}
