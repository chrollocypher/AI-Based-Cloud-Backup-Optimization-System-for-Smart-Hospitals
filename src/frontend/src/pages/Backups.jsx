import { useEffect, useState } from 'react';
import { CloudUpload, RefreshCw, RotateCcw } from 'lucide-react';
import { api, runBackups } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { DefinitionList, Drawer, Empty, ErrorBox, Loading, PageHeader, Panel, StatusTag, useToast } from '../components/ui.jsx';
import { duration, fmtDateTime, plural } from '../lib/format.js';

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'IN_PROGRESS', label: 'In progress' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'PENDING', label: 'Pending' },
];

export default function Backups() {
  const toast = useToast();
  const [filter, setFilter] = useState('');
  const jobs = useApi(() => api.listBackups(filter), [filter], { interval: 15000 });
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const rows = [...(jobs.data || [])].sort((a, b) => new Date(b.scheduled_at) - new Date(a.scheduled_at));
  const job = rows.find((j) => j.job_id === selected) || null;

  const loadDetail = (id) => {
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    api
      .getBackup(id)
      .then(setDetail)
      .catch(setDetailError)
      .finally(() => setDetailLoading(false));
  };

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      setDetailError(null);
      return undefined;
    }
    loadDetail(selected);
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const view = detail || job;
  const body = detailError && !detail ? (
    <ErrorBox error={detailError} onRetry={() => loadDetail(selected)} />
  ) : detailLoading && !detail ? (
    <Loading label="Loading job" />
  ) : view ? (
    <>
      <div className="drawer-tags"><StatusTag status={view.status} /></div>
      {view.error_message && <div className="form-error" role="alert">{view.error_message}</div>}
      <DefinitionList
        items={[
          ['Record', view.record_id],
          ['Scheduled', fmtDateTime(view.scheduled_at)],
          ['Started', fmtDateTime(view.started_at)],
          ['Completed', fmtDateTime(view.completed_at)],
          ['Duration', duration(view.started_at, view.completed_at)],
          ['S3 location', <span className="path wrap" key="s3">{view.s3_location || '—'}</span>],
          ['Execution ARN', <span className="path wrap" key="arn">{view.execution_arn || '—'}</span>],
        ]}
      />
    </>
  ) : null;

  const retry = async (id) => {
    setBusy(id);
    try {
      await api.retryBackup(id);
      toast.success(`Retried ${id}.`);
      jobs.reload(true);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
    }
  };

  const runAll = async () => {
    setBusy('run');
    try {
      const started = await runBackups();
      toast.success(started.length ? `Ran ${plural(started.length, 'backup job')}.` : 'Nothing was scheduled to back up now.');
      jobs.reload(true);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Backup jobs"
        subtitle="Runs started by the scheduler or by hand"
        actions={
          <>
            <button className="btn" onClick={() => jobs.reload(true)}>
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </button>
            <button className="btn primary" onClick={runAll} disabled={busy !== null}>
              <CloudUpload size={16} aria-hidden="true" />
              {busy === 'run' ? 'Running backups' : 'Run scheduled backups'}
            </button>
          </>
        }
      />

      <div className="chips" role="group" aria-label="Filter by status">
        {FILTERS.map((f) => (
          <button key={f.value} className={filter === f.value ? 'chip on' : 'chip'} onClick={() => setFilter(f.value)} aria-pressed={filter === f.value}>
            {f.label}
          </button>
        ))}
      </div>

      {jobs.error && !jobs.data ? (
        <ErrorBox error={jobs.error} onRetry={jobs.reload} />
      ) : !jobs.data ? (
        <Loading label="Loading jobs" />
      ) : (
        <Panel flush>
          {rows.length === 0 ? (
            <Empty title={filter ? 'No jobs with this status' : 'No backup jobs yet'}>
              {filter ? 'Try another filter.' : 'Run the scheduled backups, or back up a record from the Records page.'}
            </Empty>
          ) : (
            <div className="table-wrap">
              <table className="table clickable">
                <thead>
                  <tr>
                    <th>Job</th>
                    <th>Status</th>
                    <th>Scheduled</th>
                    <th>Duration</th>
                    <th>Destination</th>
                    <th><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((j) => (
                    <tr key={j.job_id} tabIndex={0} onClick={() => setSelected(j.job_id)} onKeyDown={(e) => e.key === 'Enter' && setSelected(j.job_id)}>
                      <td>
                        <div className="cell-strong">{j.job_id}</div>
                        <div className="cell-sub">{j.record_id}</div>
                      </td>
                      <td><StatusTag status={j.status} /></td>
                      <td>{fmtDateTime(j.scheduled_at)}</td>
                      <td>{duration(j.started_at, j.completed_at)}</td>
                      <td className="path">{j.s3_location || '—'}</td>
                      <td className="right">
                        {(j.status === 'FAILED' || j.status === 'IN_PROGRESS') && (
                          <button
                            className="btn small-btn"
                            disabled={busy === j.job_id}
                            onClick={(e) => {
                              e.stopPropagation();
                              retry(j.job_id);
                            }}
                          >
                            <RotateCcw size={14} aria-hidden="true" />
                            Retry
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}

      <Drawer
        open={!!job}
        title={job?.job_id || ''}
        onClose={() => setSelected(null)}
        footer={
          view && (view.status === 'FAILED' || view.status === 'IN_PROGRESS') ? (
            <button className="btn primary" onClick={() => retry(view.job_id)} disabled={busy === view.job_id}>
              <RotateCcw size={16} aria-hidden="true" />
              Retry job
            </button>
          ) : null
        }
      >
        {body}
      </Drawer>
    </>
  );
}
