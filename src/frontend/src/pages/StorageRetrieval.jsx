import { useState } from 'react';
import { 
  ShieldAlert, 
  Zap, 
  Coins, 
  Clock, 
  Server, 
  Flame, 
  Snowflake, 
  Thermometer, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle,
  Play
} from 'lucide-react';
import { api } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';

export default function StorageRetrieval() {
  const telemetry = useApi(api.systemTelemetry, [], { interval: 10000 });
  const costs = useApi(api.storageCostEstimate, [], { interval: 15000 });
  const alarms = useApi(api.cloudwatchAlarms, [], { interval: 15000 });
  const records = useApi(api.listRecords, []);

  const [testRecordId, setTestRecordId] = useState('EHR_10025');
  const [retrievalResult, setRetrievalResult] = useState(null);
  const [isRetrieving, setIsRetrieving] = useState(false);

  const [pipelineState, setPipelineState] = useState(null);
  const [isTriggeringPipeline, setIsTriggeringPipeline] = useState(false);

  const [prefetchResult, setPrefetchResult] = useState(null);

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
      telemetry.reload();
    } catch (err) {
      alert(`Retrieval failed: ${err.message}`);
    } finally {
      setIsRetrieving(false);
    }
  }

  // Prefetch Cache
  async function handlePrefetch() {
    try {
      const ids = ['EHR_10025', 'MON_30089', 'CT_20041'];
      const res = await api.prefetchRecords(ids, 'Predicted ER trauma admissions');
      setPrefetchResult(res);
      telemetry.reload();
    } catch (err) {
      alert(`Prefetch failed: ${err.message}`);
    }
  }

  // Trigger Step Functions Pipeline
  async function handleTriggerPipeline() {
    setIsTriggeringPipeline(true);
    try {
      const res = await api.triggerPipeline();
      setPipelineState(res);
      costs.reload();
      telemetry.reload();
      records.reload();
    } catch (err) {
      alert(`Pipeline execution failed: ${err.message}`);
    } finally {
      setIsTriggeringPipeline(false);
    }
  }

  const m = telemetry.data?.metrics;
  const costData = costs.data;
  const alarmList = alarms.data || [];

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Predictive Storage & Emergency Retrieval</h1>
          <p className="page-sub">
            Clinical criticality-aware cloud tiering, 500 ms SLA emergency watchdog, and cost optimization.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            className="btn btn-secondary" 
            onClick={handlePrefetch}
            title="Proactively prefetch emergency records into edge cache"
          >
            <Zap size={16} />
            <span>Prefetch Hot Cache</span>
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleTriggerPipeline}
            disabled={isTriggeringPipeline}
          >
            <Play size={16} />
            <span>{isTriggeringPipeline ? 'Executing Pipeline...' : 'Run Step Functions'}</span>
          </button>
        </div>
      </div>

      {/* Prefetch Notification */}
      {prefetchResult && (
        <div className="banner banner-info" style={{ marginBottom: '1.25rem' }}>
          <CheckCircle2 size={16} />
          <span>
            Prefetched {prefetchResult.prefetched_count} high-priority records into edge cache.
          </span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-4" style={{ marginBottom: '1.5rem' }}>
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

      <div className="grid grid-2" style={{ gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Emergency Retrieval Console */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldAlert size={18} className="text-danger" />
              <span>Emergency Retrieval Simulator</span>
            </h2>
            <span className="badge badge-danger">500 ms SLA Watchdog</span>
          </div>

          <div style={{ padding: '1rem 0' }}>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Test high-priority record retrieval. Emergency requests bypass standard queues and check edge cache first before pulling from S3.
            </p>

            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <input 
                type="text" 
                className="input" 
                placeholder="Enter Record ID (e.g. EHR_10025)"
                value={testRecordId}
                onChange={(e) => setTestRecordId(e.target.value)}
                style={{ flex: 1 }}
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
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Quick Select:</span>
              {['EHR_10025', 'MON_30089', 'CT_20041', 'ADMIN_9812'].map((id) => (
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
              <div style={{ 
                border: '1px solid var(--border-color)', 
                borderRadius: '8px', 
                padding: '1rem',
                backgroundColor: 'var(--surface-subtle)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span style={{ fontWeight: 600 }}>{retrievalResult.record_id}</span>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
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
                    <div style={{ color: 'var(--text-muted)' }}>Storage Tier</div>
                    <div style={{ fontWeight: 600 }}>{retrievalResult.storage_tier}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Latency</div>
                    <div style={{ fontWeight: 600, color: retrievalResult.sla_met ? 'var(--color-success)' : 'var(--color-danger)' }}>
                      {retrievalResult.retrieval_latency_ms} ms
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>SLA Target</div>
                    <div style={{ fontWeight: 600 }}>&le; {retrievalResult.sla_target_ms} ms</div>
                  </div>
                </div>

                <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  S3 Location: <code>{retrievalResult.s3_location}</code>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Storage Multi-Tier & Cost Comparison */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Coins size={18} className="text-primary" />
              <span>S3 Cloud Storage Cost Optimization</span>
            </h2>
            <span className="badge badge-success">AWS us-east-1 Model</span>
          </div>

          <div style={{ padding: '1rem 0' }}>
            <div className="grid grid-2" style={{ gap: '1rem', marginBottom: '1.25rem' }}>
              <div style={{ padding: '0.75rem', backgroundColor: 'var(--surface-subtle)', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Static S3 Standard Policy</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  ${costData?.static_standard_monthly_cost_usd?.toFixed(2) ?? '0.00'}/mo
                </div>
                <div style={{ fontSize: '0.75rem' }}>All objects in Standard tier</div>
              </div>

              <div style={{ padding: '0.75rem', backgroundColor: 'var(--surface-subtle)', borderRadius: '6px', border: '1px solid var(--color-success)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Proposed AI Multi-Tier Policy</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-success)' }}>
                  ${costData?.proposed_policy_monthly_cost_usd?.toFixed(2) ?? '0.00'}/mo
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-success)' }}>
                  Save ${costData?.projected_monthly_savings_usd?.toFixed(2) ?? '0.00'}/mo ({costData?.savings_percentage ?? 0}%)
                </div>
              </div>
            </div>

            {/* Tier Breakdown Table */}
            <div className="table-wrap">
              <table className="table" style={{ fontSize: '0.8125rem' }}>
                <thead>
                  <tr>
                    <th>Storage Tier</th>
                    <th>Records</th>
                    <th>Volume (GB)</th>
                    <th>Est. Monthly Fee</th>
                  </tr>
                </thead>
                <tbody>
                  {costData?.breakdown_by_tier?.map((item) => (
                    <tr key={item.tier}>
                      <td>
                        <span style={{ fontWeight: 600 }}>{item.tier}</span>
                      </td>
                      <td>{item.record_count}</td>
                      <td>{item.total_volume_gb.toFixed(2)} GB</td>
                      <td>${item.total_monthly_cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Clinical Safety Shield: <strong>{costData?.clinical_safety_protected_count ?? 0} records</strong> locked in high-availability tiers to safeguard emergency SLAs.
            </div>
          </div>
        </div>
      </div>

      {/* CloudWatch Alarms & Orchestration Trace */}
      <div className="grid grid-2" style={{ gap: '1.5rem' }}>
        <div className="card">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <Server size={18} />
              <span>CloudWatch Metric Alarms</span>
            </h2>
          </div>
          <div style={{ padding: '0.75rem 0' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {alarmList.map((a) => (
                <div 
                  key={a.alarm_name} 
                  style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '0.75rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: a.state === 'ALARM' ? 'rgba(239, 68, 68, 0.08)' : 'var(--surface-subtle)'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{a.alarm_name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Metric: {a.metric_name} | Value: {a.current_value}
                    </div>
                  </div>
                  <span className={`badge ${a.state === 'OK' ? 'badge-success' : 'badge-danger'}`}>
                    {a.state}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Step Functions State Machine Execution Log */}
        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h2 className="card-title flex items-center gap-2">
              <RefreshCw size={18} />
              <span>Step Functions Pipeline Status</span>
            </h2>
          </div>
          <div style={{ padding: '0.75rem 0' }}>
            {pipelineState ? (
              <div style={{ fontSize: '0.875rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Execution ID:</span>
                  <code>{pipelineState.execution_id}</code>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Status:</span>
                  <span className="badge badge-success">{pipelineState.status}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Transitions Executed:</span>
                  <span style={{ fontWeight: 600 }}>{pipelineState.transitions_executed}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Mode:</span>
                  <span>{pipelineState.mode}</span>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '1.5rem 0' }}>
                No active execution. Click <strong>"Run Step Functions"</strong> to orchestrate tiering.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
