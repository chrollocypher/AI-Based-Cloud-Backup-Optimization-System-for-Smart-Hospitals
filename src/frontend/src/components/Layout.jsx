import { NavLink, Outlet } from 'react-router-dom';
import { Activity, CalendarClock, CloudUpload, Database, LayoutDashboard, LineChart, Plus, ShieldAlert } from 'lucide-react';
import { API_BASE, api } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/storage-retrieval', label: 'Storage & Retrieval', icon: ShieldAlert },
  { to: '/records', label: 'Records', icon: Database },
  { to: '/schedule', label: 'Schedule', icon: CalendarClock },
  { to: '/backups', label: 'Backup jobs', icon: CloudUpload },
  { to: '/forecast', label: 'Forecast', icon: LineChart },
  { to: '/system', label: 'System', icon: Activity },
];

function ConnectionStatus() {
  const health = useApi(api.health, [], { interval: 30000 });
  const monitoring = useApi(api.monitoring, [], { interval: 30000 });

  let tone = 'pending';
  let label = 'Connecting';
  if (health.error && !health.data) {
    tone = 'down';
    label = 'Backend unreachable';
  } else if (health.data) {
    const healthy = monitoring.data ? monitoring.data.system_status === 'HEALTHY' : true;
    tone = healthy ? 'up' : 'warn';
    label = healthy ? 'Backend connected' : `Backend ${monitoring.data.system_status.toLowerCase()}`;
  }

  return (
    <div className="conn">
      <span className={`conn-dot conn-${tone}`} aria-hidden="true" />
      <div>
        <div className="conn-label">{label}</div>
        <div className="conn-sub">
          {health.data?.use_mock_aws ? 'Mock AWS mode' : health.data ? 'Live AWS' : API_BASE}
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <Plus size={16} strokeWidth={3} />
          </span>
          <div>
            <div className="brand-name">EHR Storage Console</div>
            <div className="brand-sub">Smart hospital cloud storage</div>
          </div>
        </div>
        <nav aria-label="Main">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <ConnectionStatus />
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
