import { useState } from 'react';
import { CalendarClock } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { ErrorBox, ForecastRange, Loading, Notice, PageHeader, Panel, useToast } from '../components/ui.jsx';
import { fmtDateTime, fmtGB, fmtMB, fmtNum, mbToGb } from '../lib/format.js';

export default function Forecast() {
  const toast = useToast();
  const latest = useApi(api.latestPrediction, []);
  const joint = useApi(api.jointForecast, [], { interval: 20000 });
  const latestAccess = useApi(api.latestAccessPrediction, [], { interval: 20000 });
  const schedule = useApi(api.getSchedule, []);
  const [form, setForm] = useState({ data_volume_mb: '8200', access_frequency: '530', active_departments: '8' });
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [applied, setApplied] = useState(true);
  const [applying, setApplying] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const [accessForm, setAccessForm] = useState({
    current_access_count: '1200',
    current_access_volume_mb: '15400',
    emergency_context_ratio: '0.05',
  });
  const [accessError, setAccessError] = useState('');
  const [runningAccess, setRunningAccess] = useState(false);
  const setAccess = (k) => (e) => setAccessForm((f) => ({ ...f, [k]: e.target.value }));

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

  const submitAccess = async (e) => {
    e.preventDefault();
    setAccessError('');
    const count = Number(accessForm.current_access_count);
    const volume = Number(accessForm.current_access_volume_mb);
    const ratio = Number(accessForm.emergency_context_ratio);
    if (!Number.isInteger(count) || count < 0) return setAccessError('Access count must be a whole number, 0 or more.');
    if (!(volume >= 0)) return setAccessError('Access volume must be 0 MB or more.');
    if (!(ratio >= 0 && ratio <= 1)) return setAccessError('Emergency context ratio must be between 0 and 1.');

    setRunningAccess(true);
    try {
      await api.predictAccess({
        current_access_count: count,
        current_access_volume_mb: volume,
        emergency_context_ratio: ratio,
        timestamp: new Date().toISOString(),
      });
      latestAccess.reload(true);
      joint.reload(true);
      toast.success('Access demand forecast updated.');
    } catch (err) {
      setAccessError(err.message);
    } finally {
      setRunningAccess(false);
    }
  };

  const p = latest.data;
  const j = joint.data;
  const a = latestAccess.data;
  const capMB = schedule.data?.capacity_threshold_mb;
  const over = p && capMB != null && p.predicted_backup_volume_mb > capMB;

  return (
    <>
      <PageHeader title="Dual Workload Forecasting" subtitle="Predict the next hour of backup volume and EHR access demand" />

      <div className="forecast-grid">
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

      {/* Dedicated Access Demand Forecast */}
      <Panel
        title="EHR Access Demand Forecast"
        subtitle="Independent BiLSTM forecast of hourly access events, volume, and emergency spikes"
      >
        <div className="grid grid-2" style={{ alignItems: 'start' }}>
          <form className="form" onSubmit={submitAccess} noValidate>
            <label>
              Current access count (last hour)
              <input type="number" min="0" step="1" value={accessForm.current_access_count} onChange={setAccess('current_access_count')} />
            </label>
            <label>
              Current access volume (MB)
              <input type="number" min="0" step="any" value={accessForm.current_access_volume_mb} onChange={setAccess('current_access_volume_mb')} />
            </label>
            <label>
              Emergency context ratio (0&ndash;1)
              <input type="number" min="0" max="1" step="0.01" value={accessForm.emergency_context_ratio} onChange={setAccess('emergency_context_ratio')} />
            </label>
            {accessError && <div className="form-error" role="alert">{accessError}</div>}
            <div className="form-actions">
              <button type="submit" className="btn primary" disabled={runningAccess}>
                {runningAccess ? 'Running forecast' : 'Run access forecast'}
              </button>
            </div>
          </form>

          <div>
            {latestAccess.error && !a ? (
              <ErrorBox error={latestAccess.error} onRetry={latestAccess.reload} />
            ) : !a ? (
              <Loading />
            ) : (
              <>
                <div className="grid grid-3">
                  <div className="soft-box">
                    <div className="small muted">Predicted access events</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{fmtNum(a.predicted_access_count)} /hr</div>
                    <div className="small">{fmtMB(a.predicted_access_volume_mb)} demand volume</div>
                  </div>
                  <div className="soft-box">
                    <div className="small muted">Emergency access spike</div>
                    <div className={a.predicted_emergency_count > 20 ? 'text-danger' : 'text-primary'} style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                      {fmtNum(a.predicted_emergency_count)} urgent
                    </div>
                    <div className="small">High-priority ER traffic</div>
                  </div>
                  <div className="soft-box">
                    <div className="small muted">Forecast horizon</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{a.forecast_horizon}</div>
                    <div className="small">Model: {a.model_version}</div>
                  </div>
                </div>
                <ForecastRange
                  low={a.confidence_interval_low}
                  high={a.confidence_interval_high}
                  predicted={a.predicted_access_volume_mb}
                />
                <p className="muted small" style={{ marginTop: '8px' }}>
                  Generated {fmtDateTime(a.timestamp)}
                </p>
              </>
            )}
          </div>
        </div>
      </Panel>

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
