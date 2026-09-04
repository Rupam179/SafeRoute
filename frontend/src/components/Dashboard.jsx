import React, { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { api } from "../api";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [byArea, setByArea] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.getAnalyticsSummary(), api.getRiskByArea()])
      .then(([s, a]) => {
        setSummary(s);
        setByArea(a);
      })
      .catch(() => setError("Could not load analytics. Is the backend running and seeded?"));
  }, []);

  if (error) return <div className="panel"><p className="status-error">{error}</p></div>;
  if (!summary) return <div className="panel"><p>Loading analytics…</p></div>;

  const typeData = Object.entries(summary.signals_by_type).map(([type, count]) => ({
    type: type.replace(/_/g, " "),
    count,
    avgSeverity: summary.avg_severity_by_type[type] || 0,
  }));

  return (
    <div className="panel dashboard">
      <h2>SafeRoute analytics</h2>

      <div className="stat-grid">
        <Stat label="Total risk signals" value={summary.total_risk_signals} />
        <Stat label="Crowd reports" value={summary.total_crowd_reports} />
        <Stat label="Road damage detections" value={summary.total_road_damage_detections} />
        <Stat label="Accident black spots" value={summary.total_accident_blackspots} />
        <Stat label="Route queries served" value={summary.total_route_queries} />
      </div>

      <h3>Signals by type</h3>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={typeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3a86ff" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h3>Top risk hot-spots (grid-bucketed)</h3>
      <table className="hotspot-table">
        <thead>
          <tr>
            <th>Lat</th>
            <th>Lng</th>
            <th>Signal count</th>
            <th>Avg severity</th>
          </tr>
        </thead>
        <tbody>
          {byArea.slice(0, 10).map((row, i) => (
            <tr key={i}>
              <td>{Number(row.lat_bucket).toFixed(3)}</td>
              <td>{Number(row.lng_bucket).toFixed(3)}</td>
              <td>{row.signal_count}</td>
              <td>{Number(row.avg_severity).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat-box">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
