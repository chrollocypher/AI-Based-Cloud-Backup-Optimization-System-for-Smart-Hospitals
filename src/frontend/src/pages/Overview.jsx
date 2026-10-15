import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CloudUpload, RefreshCw } from 'lucide-react';
import { api, runBackups } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { ActionTag, CriticalityTag, ErrorBox, Figures, Loading, Notice, PageHeader, Panel, StatusTag, useToast, Empty } from '../components/ui.jsx';
import WorkloadChart from '../components/WorkloadChart.jsx';
import { fmtGB, fmtMB, fmtNum, fmtTime, mbToGb, plural, timeAgo } from '../lib/format.js';

export default function Overview() {
  const toast = useToast();
  const summary = useApi(api.summary, [], { interval: 20000 });
  const workload = useApi(api.workload, [], { interval: 60000 });
  const schedule = useApi(api.getSchedule, [], { interval: 20000 });
  const jobs = useApi(() => api.listBackups(), [], { interval: 20000 });
  const [busy, setBusy] = useState(null);

  const reloadAll = () => {
    summary.reload(true);
    workload.reload(true);
    schedule.reload(true);
    jobs.reload(true);
  };

  if (!summary.data && summary.error) return <ErrorBox error={summary.error} onRetry={reloadAll} />;
  if (!summary.data || !schedule.data) {
    return schedule.error ? <ErrorBox error={schedule.error} onRetry={reloadAll} /> : <Loading label="Loading overview" />;
  }

  const sum = summary.data;
  const sched = schedule.data;
  const items = sched.schedule;
  const nowCount = items.filter((i) => i.action === 'BACKUP_NOW').length;
  const nextCount = items.filter((i) => i.action === 'BACKUP_NEXT').length;
  const deferCount = items.filter((i) => i.action === 'DEFER').length;

  const capGB = mbToGb(sched.capacity_threshold_mb);
  const predGB = sum.predicted_workload_gb;
  const exceeded = predGB > capGB;
  const stale = sched.total_pending_records !== sum.pending_backups || sched.is_capacity_exceeded !== exceeded;

  let headline;
  let detail;
  if (exceeded) {
    headline = `Next hour is forecast at ${fmtGB(predGB)}, ${fmtGB(predGB - capGB)} over the ${fmtGB(capGB)} limit.`;
  } else {
    headline = `Next hour is forecast at ${fmtGB(predGB)}, within the ${fmtGB(capGB)} limit.`;
  }
  if (sched.total_pending_records === 0) {
    detail = 'No records are waiting for backup.';
  } else if (exceeded) {
    detail = `Critical records go first. Of ${plural(sched.total_pending_records, 'pending record')}, ${fmtNum(nowCount)} back up now, ${fmtNum(nextCount)} wait for the next round and ${fmtNum(deferCount)} for off-peak hours.`;
  } else {
    detail = `All ${plural(sched.total_pending_records, 'pending record')} can be backed up now.`;
  }

  const run = async () => {
    setBusy('run');
    try {
      const started = await runBackups();
      toast.success(`Ran ${plural(started.length, 'backup job')}.`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
      reloadAll();
    }
  };

  const regenerate = async () => {
    setBusy('schedule');
    try {
      await api.generateSchedule();
      toast.success('Schedule regenerated.');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
      reloadAll();
    }
  };

  const recentJobs = [...(jobs.data || [])]
    .sort((a, b) => new Date(b.scheduled_at) - new Date(a.scheduled_at))
    .slice(0, 6);

  return (
    <>
      <PageHeader
        title="Overview"
        actions={
          <button className="btn" onClick={reloadAll}>
            <RefreshCw size={16} aria-hidden="true" />
            Refresh
          </button>
        }
      />

      <section className="verdict">
        <h2 className={exceeded ? 'verdict-title over' : 'verdict-title'}>{headline}</h2>
        <p>{detail}</p>
        <div className="verdict-actions">
          <button className="btn primary" onClick={run} disabled={busy !== null || nowCount === 0}>
            <CloudUpload size={16} aria-hidden="true" />
            {busy === 'run' ? 'Running backups' : `Run ${plural(nowCount, 'scheduled backup')}`}
          </button>
          <button className="btn" onClick={regenerate} disabled={busy !== null}>
            {busy === 'schedule' ? 'Regenerating' : 'Regenerate schedule'}
          </button>
        </div>
        {stale && (
          <Notice tone="warn">
            The schedule was generated before the latest changes and may not match the numbers below. Regenerate it to bring it up to date.
          </Notice>
        )}
      </section>

      <Figures
        items={[
          { label: 'Pending backups', value: fmtNum(sum.pending_backups), note: `${fmtNum(sum.critical_pending)} critical`, tone: sum.critical_pending > 0 ? 'crit' : undefined },
          { label: 'Completed today', value: fmtNum(sum.completed_today) },
          { label: 'Failed today', value: fmtNum(sum.failed_today), tone: sum.failed_today > 0 ? 'crit' : undefined },
          { label: 'Registered data', value: fmtGB(sum.current_workload_gb), note: 'across all records' },
          { label: 'Cloud storage used', value: fmtGB(sum.storage_used_gb) },
        ]}
      />

      <Panel title="Workload" subtitle="Actual and predicted data volume per hour, last 6 hours" className="chart-panel">
        {workload.data ? (
          <WorkloadChart points={workload.data} capacityGB={capGB} />
        ) : workload.error ? (
          <ErrorBox error={workload.error} onRetry={workload.reload} />
        ) : (
          <Loading />
        )}
      </Panel>

      <div className="two-col">
        <Panel
          title="Backup queue"
          subtitle={`Generated ${timeAgo(sched.generated_at)}`}
          aside={<Link to="/schedule">Open schedule</Link>}
          flush
        >
          {items.length === 0 ? (
            <Empty title="Queue is empty">Every registered record has been backed up.</Empty>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Record</th>
                    <th>Criticality</th>
                    <th className="num">Size</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.slice(0, 6).map((it) => (
                    <tr key={it.record_id}>
                      <td>
                        <div className="cell-strong">{it.record_id}</div>
                        <div className="cell-sub">{it.department}</div>
                      </td>
                      <td><CriticalityTag level={it.criticality} /></td>
                      <td className="num">{fmtMB(it.data_size_mb)}</td>
                      <td><ActionTag action={it.action} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title="Recent backup jobs" aside={<Link to="/backups">All jobs</Link>} flush>
          {recentJobs.length === 0 ? (
            <Empty title="No backups yet">Jobs appear here once a backup has run.</Empty>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Record</th>
                    <th>Status</th>
                    <th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {recentJobs.map((j) => (
                    <tr key={j.job_id}>
                      <td>
                        <div className="cell-strong">{j.record_id}</div>
                        <div className="cell-sub">{j.job_id}</div>
                      </td>
                      <td><StatusTag status={j.status} /></td>
                      <td>{fmtTime(j.started_at || j.scheduled_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
