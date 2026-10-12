import { useState } from 'react';
import { CalendarClock, Activity, ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { ErrorBox, ForecastRange, Loading, Notice, PageHeader, Panel, useToast } from '../components/ui.jsx';
import { fmtDateTime, fmtGB, fmtMB, fmtNum, mbToGb } from '../lib/format.js';

export default function Forecast() {
  const toast = useToast();
  const latest = useApi(api.latestPrediction, []);
  const joint = useApi(api.jointForecast, [], { interval: 20000 });
  const schedule = useApi(api.getSchedule, []);
  const [form, setForm] = useState({ data_volume_mb: '8200', access_frequency: '530', active_departments: '8' });
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [applied, setApplied] = useState(true);
  const [applying, setApplying] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    const volume = Number(form.data_volume_mb);
    const freq = Number(form.access_frequency);
    const depts = Number(form.active_departments);
    if (!(volume > 0)) return setError('Data volume must be greater than 0 MB.');
    if (!Number.isInteger(freq) || freq < 0) return setError('Access frequency must be a whole number, 0 or more.');
    if (!Number.isInteger(depts) || depts < 0) return setError('Active departments must be a whole number, 0 or more.');

    setRunning(true);
    try {
      await api.predict({ data_volume_mb: volume, access_frequency: freq, active_departments: depts, timestamp: new Date().toISOString() });
      setApplied(false);
      latest.reload(true);
      joint.reload(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  const apply = async () => {
    setApplying(true);
    try {
      await api.generateSchedule();
      setApplied(true);
      toast.success('Schedule regenerated with the new forecast.');
      schedule.reload(true);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setApplying(false);
    }
  };

  const p = latest.data;
  const j = joint.data;
  const capMB = schedule.data?.capacity_threshold_mb;
  const over = p && capMB != null && p.predicted_backup_volume_mb > capMB;

  return (
    <>
      <PageHeader title="Dual Workload Forecasting" subtitle="Predict the next hour of backup volume and EHR access demand" />

      <div className="forecast-grid" style={{ marginBottom: '1.5rem' }}>
        <Panel title="Run a forecast" subtitle="Enter hospital workload observations">
          <form className="form" onSubmit={submit} noValidate>
            <label>
              Current data volume (MB)
              <input type="number" min="0" step="any" value={form.data_volume_mb} onChange={set('data_volume_mb')} />
            </label>
            <label>
              Access frequency
              <input type="number" min="0" step="1" value={form.access_frequency} onChange={set('access_frequency')} />
            </label>
            <label>
              Active departments
              <input type="number" min="0" step="1" value={form.active_departments} onChange={set('active_departments')} />
            </label>
            {error && <div className="form-error" role="alert">{error}</div>}
            <div className="form-actions">
              <button type="submit" className="btn primary" disabled={running}>{running ? 'Running forecast' : 'Run forecast'}</button>
            </div>
          </form>
        </Panel>

        <Panel title="Backup Volume Forecast (LSTM Baseline)" subtitle={p ? `${p.forecast_horizon} ahead, generated ${fmtDateTime(p.timestamp)}` : undefined}>
          {latest.error && !p ? (
            <ErrorBox error={latest.error} onRetry={latest.reload} />
          ) : !p ? (
            <Loading />
          ) : (
            <>
              <div className="big-figure">
                <span className="big-number">{fmtGB(mbToGb(p.predicted_backup_volume_mb))}</span>
                <span className="muted">{fmtNum(p.predicted_backup_volume_mb, 0)} MB predicted</span>
              </div>
              <ForecastRange
                low={p.confidence_interval_low}
                high={p.confidence_interval_high}
                predicted={p.predicted_backup_volume_mb}
                capacityMB={capMB}
              />
              {capMB != null && (
                <p className={over ? 'verdict-line over' : 'verdict-line'}>
                  {over
                    ? `${fmtMB(p.predicted_backup_volume_mb - capMB)} over the capacity limit, so the scheduler will throttle low-priority backups.`
                    : 'Within the capacity limit, so every pending record can be backed up now.'}
                </p>
              )}
              <p className="muted small">Model: {p.model_version}</p>
              {!applied && (
                <Notice
                  tone="warn"
                  action={
                    <button className="btn small-btn" onClick={apply} disabled={applying}>
                      <CalendarClock size={14} aria-hidden="true" />
                      {applying ? 'Regenerating' : 'Regenerate schedule'}
                    </button>
                  }
                >
                  The current schedule was built on the previous forecast.
                </Notice>
              )}
              {applied && <p className="small"><Link to="/schedule">View the schedule</Link></p>}
            </>
          )}
        </Panel>
      </div>

      {/* Joint Access Demand Card */}
      {j && (
        <Panel title="EHR Access Demand & Joint Intensity" subtitle="BiLSTM access forecast guiding storage-tier migration decisions">
          <div className="grid grid-3" style={{ gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ padding: '0.75rem', backgroundColor: 'var(--surface-subtle)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Predicted Access Events</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{j.access_forecast.predicted_access_count} events/hr</div>
              <div style={{ fontSize: '0.75rem' }}>{fmtMB(j.access_forecast.predicted_access_volume_mb)} demand volume</div>
            </div>

            <div style={{ padding: '0.75rem', backgroundColor: 'var(--surface-subtle)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Emergency Access Spike</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: j.access_forecast.predicted_emergency_count > 20 ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                {j.access_forecast.predicted_emergency_count} urgent requests
              </div>
              <div style={{ fontSize: '0.75rem' }}>High priority ER traffic</div>
            </div>

            <div style={{ padding: '0.75rem', backgroundColor: 'var(--surface-subtle)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Workload Intensity</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-primary)' }}>{j.workload_intensity_level}</div>
              <div style={{ fontSize: '0.75rem' }}>Model: {j.access_forecast.model_version}</div>
            </div>
          </div>

          <div style={{ padding: '0.75rem', backgroundColor: 'rgba(59, 130, 246, 0.08)', borderRadius: '6px', fontSize: '0.875rem' }}>
            <strong>Cloud Tiering Directive: </strong>{j.recommendation}
          </div>
        </Panel>
      )}
    </>
  );
}
