import { useState } from 'react';
import { 
  ShieldAlert, 
  Zap, 
  Coins, 
  Server, 
  RefreshCw, 
  CheckCircle2, 
  Play,
  ArrowRightLeft,
  Gauge
} from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import { Empty, ErrorBox, Loading, useToast } from '../components/ui.jsx';
import { fmtDateTime, fmtNum } from '../lib/format.js';

const TIERS = ['HOT', 'WARM', 'COLD', 'ARCHIVE'];
const QUICK_IDS = ['EHR_10025', 'MON_30089', 'CT_20041', 'ADMIN_9812'];
const JOB_FILTERS = [
  { value: 'all', label: 'All requests' },
  { value: 'emergency', label: 'Emergency' },
  { value: 'standard', label: 'Standard' },
];

export default function StorageRetrieval() {
  const toast = useToast();
  const telemetry = useApi(api.systemTelemetry, [], { interval: 10000 });
  const costs = useApi(api.storageCostEstimate, [], { interval: 15000 });
  const alarms = useApi(api.cloudwatchAlarms, [], { interval: 15000 });
  const metrics = useApi(api.retrievalMetrics, [], { interval: 10000 });
  const records = useApi(api.listRecords, []);

  const [testRecordId, setTestRecordId] = useState('EHR_10025');
  const [retrievalResult, setRetrievalResult] = useState(null);
  const [isRetrieving, setIsRetrieving] = useState(false);

  const [pipelineState, setPipelineState] = useState(null);
  const [isTriggeringPipeline, setIsTriggeringPipeline] = useState(false);

  const [prefetchResult, setPrefetchResult] = useState(null);

  const [jobFilter, setJobFilter] = useState('all');
  const jobs = useApi(
    () => api.listRetrievalJobs(jobFilter === 'all' ? undefined : jobFilter === 'emergency'),
    [jobFilter],
    { interval: 15000 },
  );

  const [tierRecordId, setTierRecordId] = useState('');
  const [tierTarget, setTierTarget] = useState('COLD');
  const [tierReason, setTierReason] = useState('ML access-demand optimization');
  const [tierResult, setTierResult] = useState(null);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const reloadAll = () => {
    telemetry.reload();
    costs.reload();
    alarms.reload();
    metrics.reload();
    records.reload();
  };

  // Trigger Emergency Retrieval
  async function handleRetrieve(isEmergency = true) {
    if (!testRecordId) return;
    setIsRetrieving(true);
    try {
      const res = await api.retrieveRecord({
        record_id: testRecordId,
        is_emergency: isEmergency,
        department: 'Emergency Trauma',
        reason: 'Acute emergency clinical evaluation'
      });
      setRetrievalResult(res);
      telemetry.reload(true);
      metrics.reload(true);
      jobs.reload(true);
    } catch (err) {
      toast.error(`Retrieval failed: ${err.message}`);
    } finally {
      setIsRetrieving(false);
    }
  }

  // Prefetch Cache
  async function handlePrefetch() {
    try {
      const res = await api.prefetchRecords(QUICK_IDS, 'Predicted ER trauma admissions');
      setPrefetchResult(res);
      telemetry.reload(true);
      metrics.reload(true);
      toast.success(`Prefetched ${res.prefetched_count} high-priority records into edge cache.`);
    } catch (err) {
      toast.error(`Prefetch failed: ${err.message}`);
    }
  }

  // Trigger Step Functions Pipeline
  async function handleTriggerPipeline() {
    setIsTriggeringPipeline(true);
    try {
      const res = await api.triggerPipeline();
      setPipelineState(res);
      costs.reload(true);
      telemetry.reload(true);
      records.reload(true);
      toast.success(`Pipeline ${res.execution_id} ${res.status === 'SUCCEEDED' ? 'completed' : 'started'}.`);
    } catch (err) {
      toast.error(`Pipeline execution failed: ${err.message}`);
    } finally {
      setIsTriggeringPipeline(false);
    }
  }

  // Storage tier transition
  async function handleTransition(e) {
    e.preventDefault();
    if (!tierRecordId) return;
    setIsTransitioning(true);
    try {
      const res = await api.transitionTier(tierRecordId, tierTarget, tierReason);
      setTierResult(res);
      costs.reload(true);
      telemetry.reload(true);
      records.reload(true);
      toast.success(`${res.record_id}: ${res.previous_tier} → ${res.new_tier}.`);
    } catch (err) {
      toast.error(`Tier transition failed: ${err.message}`);
    } finally {
      setIsTransitioning(false);
    }
  }

  const m = telemetry.data?.metrics;
  const metric = metrics.data;
  const costData = costs.data;
  const alarmList = alarms.data || [];
  const jobList = jobs.data || [];
  const recordOptions = records.data || [];

  if (telemetry.error && !telemetry.data && costs.error && !costs.data) {
    return <ErrorBox error={telemetry.error || costs.error} onRetry={reloadAll} />;
  }

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Predictive Storage & Emergency Retrieval</h1>
          <p className="page-sub">
            Clinical criticality-aware cloud tiering, 500 ms SLA emergency watchdog, and cost optimization.
          </p>
        </div>
        <div className="page-actions">
          <button className="btn btn-secondary" onClick={reloadAll} title="Refresh all telemetry">
            <RefreshCw size={16} aria-hidden="true" />
            <span>Refresh</span>
          </button>
          <button
            className="btn btn-secondary"
            onClick={handlePrefetch}
            title="Proactively prefetch emergency records into edge cache"
          >
            <Zap size={16} aria-hidden="true" />
            <span>Prefetch Hot Cache</span>
          </button>
          <button
            className="btn btn-primary"
            onClick={handleTriggerPipeline}
            disabled={isTriggeringPipeline}
          >
            <Play size={16} aria-hidden="true" />
            <span>{isTriggeringPipeline ? 'Executing Pipeline...' : 'Run Step Functions'}</span>
          </button>
        </div>
      </div>

      {/* Prefetch Notification */}
      {prefetchResult && (
        <div className="banner banner-info" role="status">
          <CheckCircle2 size={16} aria-hidden="true" />
          <span>
            Prefetched {prefetchResult.prefetched_count} high-priority records into edge cache.
          </span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-4">
        <div className="card stat-card">
          <div className="stat-label">Emergency Latency</div>
          <div className="stat-val">
            {m?.['1_retrieval_latency']?.average_emergency_latency_ms ?? 0} ms
          </div>
          <div className="stat-sub">Target SLA &lt; 500 ms</div>
        </div>

        <div className="card stat-card">
          <div className="stat-label">Critical Availability</div>
          <div className="stat-val">
            {m?.['2_critical_record_availability_percent'] ?? 100}%
          </div>
          <div className="stat-sub">Fulfilled within SLA target</div>
        </div>

        <div className="card stat-card">
          <div className="stat-label">Edge Cache Hit Rate</div>
          <div className="stat-val">
            {m?.['4_cache_hit_rate_percent'] ?? 0}%
          </div>
          <div className="stat-sub">Sub-25ms memory lookup</div>
        </div>

        <div className="card stat-card">
          <div className="stat-label">Monthly Cloud Savings</div>
          <div className="stat-val text-success">
            {costData?.savings_percentage ?? 0}%
          </div>
          <div className="stat-sub">
            ${costData?.projected_monthly_savings_usd ?? 0}/mo saved vs Standard
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        {/* Emergency Retrieval Console */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <ShieldAlert size={18} className="text-danger" aria-hidden="true" />
              <span>Emergency Retrieval Simulator</span>
            </h2>
            <span className="badge badge-danger">500 ms SLA Watchdog</span>
          </div>

          <div>
            <p className="small muted">
              Test high-priority record retrieval. Emergency requests bypass standard queues and check edge cache first before pulling from S3.
            </p>

            <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '0.75rem', margin: '1rem 0' }}>
              <input
                type="text"
                className="input"
                placeholder="Enter Record ID (e.g. EHR_10025)"
                value={testRecordId}
                onChange={(e) => setTestRecordId(e.target.value)}
                aria-label="Record ID to retrieve"
              />
              <button
                className="btn btn-primary"
                onClick={() => handleRetrieve(true)}
                disabled={isRetrieving || !testRecordId}
              >
                {isRetrieving ? 'Retrieving...' : 'Emergency Retrieve'}
              </button>
            </div>

            {/* Quick Select Buttons */}
            <div className="flex items-center gap-2" style={{ flexWrap: 'wrap', marginBottom: '0.5rem' }}>
              <span className="small muted">Quick select:</span>
              {QUICK_IDS.map((id) => (
                <button
                  key={id}
                  className="btn btn-ghost btn-xs"
                  onClick={() => setTestRecordId(id)}
                >
                  {id}
                </button>
              ))}
            </div>

            {/* Retrieval Outcome Display */}
            {retrievalResult && (
              <div className="soft-box" style={{ marginTop: '1rem' }}>
                <div className="flex items-center justify-between" style={{ marginBottom: '0.75rem' }}>
                  <span style={{ fontWeight: 600 }}>{retrievalResult.record_id}</span>
                  <div className="flex gap-2">
                    <span className={`badge ${retrievalResult.cache_hit ? 'badge-success' : 'badge-neutral'}`}>
                      {retrievalResult.cache_hit ? 'CACHE HIT' : 'CACHE MISS'}
                    </span>
                    <span className={`badge ${retrievalResult.sla_met ? 'badge-success' : 'badge-danger'}`}>
                      {retrievalResult.sla_met ? 'SLA MET' : 'SLA VIOLATED'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-3" style={{ fontSize: '0.8125rem', gap: '0.5rem' }}>
                  <div>
                    <div className="muted">Storage tier</div>
                    <div style={{ fontWeight: 600 }}>{retrievalResult.storage_tier}</div>
                  </div>
                  <div>
                    <div className="muted">Latency</div>
                    <div className={retrievalResult.sla_met ? 'text-success' : 'text-danger'} style={{ fontWeight: 600 }}>
                      {retrievalResult.retrieval_latency_ms} ms
                    </div>
                  </div>
                  <div>
                    <div className="muted">SLA target</div>
                    <div style={{ fontWeight: 600 }}>&le; {retrievalResult.sla_target_ms} ms</div>
                  </div>
                </div>

                <div className="small muted" style={{ marginTop: '0.75rem' }}>
                  S3 location: <code className="mono">{retrievalResult.s3_location}</code>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Storage Multi-Tier & Cost Comparison */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Coins size={18} className="text-primary" aria-hidden="true" />
              <span>S3 Cloud Storage Cost Optimization</span>
            </h2>
            <span className="badge badge-success">AWS {costData?.pricing_region || 'us-east-1'} model</span>
          </div>

          {costs.error && !costData ? (
            <ErrorBox error={costs.error} onRetry={costs.reload} />
          ) : !costData ? (
            <Loading label="Loading cost model" />
          ) : (
            <div>
              <div className="grid grid-2" style={{ marginBottom: '1.25rem' }}>
                <div className="soft-box">
                  <div className="small muted">Static S3 Standard policy</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                    ${fmtNum(costData.static_standard_monthly_cost_usd, 2)}/mo
                  </div>
                  <div className="small">All objects in Standard tier</div>
                </div>

                <div className="soft-box soft-box-accent">
                  <div className="small muted">Proposed AI multi-tier policy</div>
                  <div className="text-success" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                    ${fmtNum(costData.proposed_policy_monthly_cost_usd, 2)}/mo
                  </div>
                  <div className="small text-success">
                    Save ${fmtNum(costData.projected_monthly_savings_usd, 2)}/mo ({costData.savings_percentage}%)
                  </div>
                </div>
              </div>

              {/* Tier Breakdown Table */}
              <div className="table-wrap">
                <table className="table" style={{ fontSize: '0.8125rem' }}>
                  <thead>
                    <tr>
                      <th>Storage tier</th>
                      <th className="num">Records</th>
                      <th className="num">Volume</th>
                      <th className="num">Est. monthly fee</th>
                    </tr>
                  </thead>
                  <tbody>
                    {costData.breakdown_by_tier?.map((item) => (
                      <tr key={item.tier}>
                        <td><span className="cell-strong">{item.tier}</span></td>
                        <td className="num">{fmtNum(item.record_count)}</td>
                        <td className="num">{fmtNum(item.total_volume_gb, 2)} GB</td>
                        <td className="num">${fmtNum(item.total_monthly_cost_usd, 4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="small muted" style={{ marginTop: '1rem' }}>
                Clinical safety shield: <strong>{costData.clinical_safety_protected_count} records</strong> locked in high-availability tiers to safeguard emergency SLAs.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Retrieval metrics + Tier transition */}
      <div className="grid grid-2">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Gauge size={18} aria-hidden="true" />
              <span>Retrieval Performance Metrics</span>
            </h2>
            <span className="badge badge-neutral">GET /retrieval/metrics</span>
          </div>

          {metrics.error && !metric ? (
            <ErrorBox error={metrics.error} onRetry={metrics.reload} />
          ) : !metric ? (
            <Loading label="Loading retrieval metrics" />
          ) : (
            <div>
              <div className="grid grid-2" style={{ marginBottom: '1rem' }}>
                <div className="soft-box">
                  <div className="small muted">Total retrieval requests</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{fmtNum(metric.total_retrieval_requests)}</div>
                  <div className="small">{fmtNum(metric.emergency_requests_count)} emergency</div>
                </div>
                <div className="soft-box">
                  <div className="small muted">Cache hit rate</div>
                  <div className="text-success" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                    {fmtNum(metric.cache_hit_rate_percent, 1)}%
                  </div>
                  <div className="small">{fmtNum(metric.cache_hits_count)} cache hits</div>
                </div>
                <div className="soft-box">
                  <div className="small muted">Emergency latency (avg)</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{fmtNum(metric.average_emergency_latency_ms, 1)} ms</div>
                  <div className="small">SLA target 500 ms</div>
                </div>
                <div className={`soft-box${metric.sla_violations_count > 0 ? '' : ' soft-box-accent'}`}>
                  <div className="small muted">SLA violations</div>
                  <div className={metric.sla_violations_count > 0 ? 'text-danger' : 'text-success'} style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                    {fmtNum(metric.sla_violations_count)}
                  </div>
                  <div className="small">{fmtNum(metric.sla_violation_rate_percent, 1)}% of requests</div>
                </div>
              </div>

              {Object.keys(metric.average_latency_by_tier_ms || {}).length > 0 && (
                <>
                  <h3 className="small muted">Average latency by storage tier</h3>
                  <dl className="deflist">
                    {Object.entries(metric.average_latency_by_tier_ms).map(([tier, ms]) => (
                      <div key={tier}>
                        <dt>{tier}</dt>
                        <dd>{fmtNum(ms, 1)} ms</dd>
                      </div>
                    ))}
                  </dl>
                </>
              )}
            </div>
          )}
        </div>

        {/* Tier transition console */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <ArrowRightLeft size={18} aria-hidden="true" />
              <span>Storage Tier Transition</span>
            </h2>
            <span className="badge badge-neutral">POST /storage/tier-transitions</span>
          </div>

          <form className="form" onSubmit={handleTransition}>
            <label>
              Record ID
              <input
                className="input"
                list="tier-record-options"
                placeholder="EHR_10025"
                value={tierRecordId}
                onChange={(e) => setTierRecordId(e.target.value)}
                required
              />
              <datalist id="tier-record-options">
                {recordOptions.map((r) => (
                  <option key={r.record_id} value={r.record_id} />
                ))}
              </datalist>
            </label>
            <label>
              Target tier
              <select value={tierTarget} onChange={(e) => setTierTarget(e.target.value)}>
                {TIERS.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label>
              Reason
              <input
                className="input"
                value={tierReason}
                onChange={(e) => setTierReason(e.target.value)}
              />
            </label>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={isTransitioning || !tierRecordId}>
                {isTransitioning ? 'Transitioning...' : 'Move record'}
              </button>
            </div>
          </form>

          {tierResult && (
            <div className="soft-box">
              <div className="flex items-center justify-between" style={{ marginBottom: '0.5rem' }}>
                <span className="cell-strong">{tierResult.record_id}</span>
                <span className={`badge ${tierResult.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}`}>{tierResult.status}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="badge badge-neutral">{tierResult.previous_tier}</span>
                <ArrowRightLeft size={14} aria-hidden="true" />
                <span className="badge badge-success">{tierResult.new_tier}</span>
              </div>
              <div className="small muted" style={{ marginTop: '0.5rem' }}>
                AWS class {tierResult.aws_storage_class} · {fmtDateTime(tierResult.transitioned_at)}
              </div>
              {tierResult.safety_rule_applied && (
                <div className="small text-danger" style={{ marginTop: '0.25rem' }}>
                  Clinical safety rule was applied to protect this critical record.
                </div>
              )}
              <div className="small muted" style={{ marginTop: '0.375rem' }}>
                <code className="mono">{tierResult.s3_location}</code>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Emergency retrieval job history */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <ShieldAlert size={18} aria-hidden="true" />
            <span>Retrieval History</span>
          </h2>
          <div className="chips" role="group" aria-label="Filter retrieval jobs">
            {JOB_FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                className={jobFilter === f.value ? 'chip on' : 'chip'}
                onClick={() => setJobFilter(f.value)}
                aria-pressed={jobFilter === f.value}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {jobs.error && !jobs.data ? (
          <ErrorBox error={jobs.error} onRetry={jobs.reload} />
        ) : !jobs.data ? (
          <Loading label="Loading retrieval jobs" />
        ) : jobList.length === 0 ? (
          <Empty title="No retrieval jobs yet">
            Run an emergency retrieval or prefetch to populate this history.
          </Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Record</th>
                  <th>Type</th>
                  <th>Storage tier</th>
                  <th>Cache</th>
                  <th className="num">Latency</th>
                  <th>SLA</th>
                  <th>Requested</th>
                </tr>
              </thead>
              <tbody>
                {jobList.map((j) => (
                  <tr key={j.retrieval_id}>
                    <td>
                      <div className="cell-strong">{j.record_id}</div>
                      <div className="cell-sub">{j.retrieval_id}</div>
                    </td>
                    <td>
                      <span className={`badge ${j.is_emergency ? 'badge-danger' : 'badge-neutral'}`}>
                        {j.is_emergency ? 'Emergency' : 'Standard'}
                      </span>
                    </td>
                    <td>{j.storage_tier}</td>
                    <td>
                      <span className={`badge ${j.cache_hit ? 'badge-success' : 'badge-neutral'}`}>
                        {j.cache_hit ? 'Hit' : 'Miss'}
                      </span>
                    </td>
                    <td className="num">{fmtNum(j.retrieval_latency_ms, 1)} ms</td>
                    <td>
                      <span className={`badge ${j.sla_met ? 'badge-success' : 'badge-danger'}`}>
                        {j.sla_met ? 'Met' : 'Violated'}
                      </span>
                    </td>
                    <td>{fmtDateTime(j.requested_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CloudWatch Alarms & Orchestration Trace */}
      <div className="grid grid-2">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Server size={18} aria-hidden="true" />
              <span>CloudWatch Metric Alarms</span>
            </h2>
          </div>
          {alarms.error && !alarms.data ? (
            <ErrorBox error={alarms.error} onRetry={alarms.reload} />
          ) : !alarms.data ? (
            <Loading label="Loading alarms" />
          ) : alarmList.length === 0 ? (
            <Empty title="No alarms configured" />
          ) : (
            <div className="stack">
              {alarmList.map((a) => (
                <div key={a.alarm_name} className="soft-box flex items-center justify-between">
                  <div>
                    <div className="cell-strong">{a.alarm_name}</div>
                    <div className="small muted">Metric: {a.metric_name} | Value: {a.current_value}</div>
                  </div>
                  <span className={`badge ${a.state === 'OK' ? 'badge-success' : 'badge-danger'}`}>
                    {a.state}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Step Functions State Machine Execution Log */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <RefreshCw size={18} aria-hidden="true" />
              <span>Step Functions Pipeline Status</span>
            </h2>
          </div>
          {pipelineState ? (
            <div>
              <dl className="deflist">
                <div>
                  <dt>Execution ID</dt>
                  <dd><code className="mono">{pipelineState.execution_id}</code></dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd><span className={`badge ${pipelineState.status === 'SUCCEEDED' ? 'badge-success' : 'badge-neutral'}`}>{pipelineState.status}</span></dd>
                </div>
                <div>
                  <dt>Transitions executed</dt>
                  <dd>{pipelineState.transitions_executed ?? '—'}</dd>
                </div>
                <div>
                  <dt>Forecast intensity</dt>
                  <dd>{pipelineState.forecast_intensity ?? '—'}</dd>
                </div>
                <div>
                  <dt>Mode</dt>
                  <dd>{pipelineState.mode}</dd>
                </div>
                <div>
                  <dt>Started</dt>
                  <dd>{fmtDateTime(pipelineState.started_at)}</dd>
                </div>
              </dl>
            </div>
          ) : (
            <Empty title="No active execution">
              Click <strong>Run Step Functions</strong> to orchestrate tiering. Previous runs are listed on the System page.
            </Empty>
          )}
        </div>
      </div>
    </div>
  );
}
