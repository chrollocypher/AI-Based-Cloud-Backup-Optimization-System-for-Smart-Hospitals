import { useState } from 'react';
import { CloudUpload, RefreshCw } from 'lucide-react';
import { api, runBackups } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { ActionTag, CapacityGauge, CriticalityTag, Empty, ErrorBox, Figures, Loading, PageHeader, Panel, useToast } from '../components/ui.jsx';
import { fmtDateTime, fmtMB, fmtNum, plural } from '../lib/format.js';

export default function Schedule() {
  const toast = useToast();
  const schedule = useApi(api.getSchedule, []);
  const [busy, setBusy] = useState(null);

  if (schedule.error && !schedule.data) return <ErrorBox error={schedule.error} onRetry={schedule.reload} />;
  if (!schedule.data) return <Loading label="Loading schedule" />;

  const s = schedule.data;
  const nextCount = s.schedule.filter((i) => i.action === 'BACKUP_NEXT').length;
  const maxScore = Math.max(5, ...s.schedule.map((i) => i.priority_score));

  const regenerate = async () => {
    setBusy('schedule');
    try {
      await api.generateSchedule();
      toast.success('Schedule regenerated.');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
      schedule.reload(true);
    }
  };

  const run = async () => {
    setBusy('run');
    try {
      const jobs = await runBackups();
      toast.success(`Ran ${plural(jobs.length, 'backup job')}.`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
      schedule.reload(true);
    }
  };

  return (
    <>
      <PageHeader
        title="Schedule"
        subtitle={`Generated ${fmtDateTime(s.generated_at)}`}
        actions={
          <>
            <button className="btn" onClick={regenerate} disabled={busy !== null}>
              <RefreshCw size={16} aria-hidden="true" />
              {busy === 'schedule' ? 'Regenerating' : 'Regenerate'}
            </button>
            <button className="btn primary" onClick={run} disabled={busy !== null || s.scheduled_now_count === 0}>
              <CloudUpload size={16} aria-hidden="true" />
              {busy === 'run' ? 'Running backups' : `Run ${plural(s.scheduled_now_count, 'backup')} now`}
            </button>
          </>
        }
      />

      <Panel
        title={s.is_capacity_exceeded ? 'Forecast is over the capacity limit' : 'Forecast is within the capacity limit'}
        subtitle={
          s.is_capacity_exceeded
            ? 'The scheduler is throttling: critical records first, then high-priority scans that fit, the rest later.'
            : 'The scheduler is running every pending record at once.'
        }
      >
        <CapacityGauge predictedMB={s.predicted_workload_mb} capacityMB={s.capacity_threshold_mb} />
      </Panel>

      <Figures
        items={[
          { label: 'Pending records', value: fmtNum(s.total_pending_records) },
          { label: 'Back up now', value: fmtNum(s.scheduled_now_count) },
          { label: 'Next round', value: fmtNum(nextCount) },
          { label: 'Deferred', value: fmtNum(s.deferred_count) },
        ]}
      />

      <Panel title="Queue, highest priority first" flush>
        {s.schedule.length === 0 ? (
          <Empty title="Nothing to schedule">Every registered record has been backed up. Register a record to see it queued here.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Record</th>
                  <th>Criticality</th>
                  <th>Priority score</th>
                  <th className="num">Size</th>
                  <th>Action</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {s.schedule.map((it) => (
                  <tr key={it.record_id}>
                    <td>
                      <div className="cell-strong">{it.record_id}</div>
                      <div className="cell-sub">{it.record_type}, {it.department}</div>
                    </td>
                    <td><CriticalityTag level={it.criticality} /></td>
                    <td>
                      <div className="score">
                        <div className="score-bar"><div style={{ width: `${(it.priority_score / maxScore) * 100}%` }} /></div>
                        <span>{fmtNum(it.priority_score, 2)}</span>
                      </div>
                    </td>
                    <td className="num">{fmtMB(it.data_size_mb)}</td>
                    <td><ActionTag action={it.action} /></td>
                    <td className="reason">{it.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
