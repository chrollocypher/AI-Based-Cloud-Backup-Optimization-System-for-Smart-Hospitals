import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const INK = '#12232C';
const TEAL = '#0B6B70';
const RED = '#C7362B';
const GRID = '#E3E9EC';
const MUTED = '#5B6E79';

export default function WorkloadChart({ points, capacityGB }) {
  const top = Math.max(capacityGB ?? 0, ...points.map((p) => Math.max(p.actual_gb, p.predicted_gb)));
  return (
    <div>
      <div className="chart-legend">
        <span><i className="swatch swatch-actual" />Actual</span>
        <span><i className="swatch swatch-predicted" />Predicted</span>
        {capacityGB != null && <span><i className="swatch swatch-limit" />Capacity limit</span>}
      </div>
      <div className="chart-box" role="img" aria-label="Line chart of actual and predicted workload per hour, with the capacity limit">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 12, right: 24, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={GRID} vertical={false} />
            <XAxis dataKey="timestamp" tick={{ fill: MUTED, fontSize: 12 }} tickLine={false} axisLine={{ stroke: GRID }} />
            <YAxis
              domain={[0, Math.ceil(top * 1.15)]}
              tick={{ fill: MUTED, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={58}
              tickFormatter={(v) => `${v} GB`}
            />
            <Tooltip
              formatter={(v, name) => [`${Number(v).toFixed(2)} GB`, name === 'actual_gb' ? 'Actual' : 'Predicted']}
              contentStyle={{ borderRadius: 4, border: `1px solid ${GRID}`, boxShadow: 'none', fontSize: 13 }}
            />
            {capacityGB != null && <ReferenceLine y={capacityGB} stroke={RED} strokeDasharray="2 4" strokeWidth={1.5} />}
            <Line type="monotone" dataKey="actual_gb" stroke={INK} strokeWidth={2.25} dot={{ r: 3, fill: INK }} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="predicted_gb" stroke={TEAL} strokeWidth={2.25} strokeDasharray="6 4" dot={{ r: 3, fill: '#fff', stroke: TEAL, strokeWidth: 2 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
