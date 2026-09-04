import React from "react";

const LABEL_META = {
  fastest: { emoji: "⚡", title: "Fastest", color: "#3a86ff" },
  balanced: { emoji: "⚖️", title: "Balanced", color: "#ffb703" },
  safest: { emoji: "🛡️", title: "Safest", color: "#2a9d8f" },
};

export default function RouteComparisonCards({ routes, note, selectedLabel, onSelect }) {
  if (!routes || routes.length === 0) return null;

  return (
    <div className="panel">
      <h2>Route comparison</h2>
      <p className="comparison-note">{note}</p>

      <div className="route-cards">
        {routes.map((r) => {
          const meta = LABEL_META[r.label];
          return (
            <div
              key={r.label}
              className={`route-card ${selectedLabel === r.label ? "selected" : ""}`}
              style={{ borderColor: meta.color }}
              onClick={() => onSelect(r.label)}
            >
              <div className="route-card-title" style={{ color: meta.color }}>
                {meta.emoji} {meta.title}
              </div>
              <div className="route-card-stat">
                <span>{r.duration_min} min</span>
                <span>{r.distance_km} km</span>
              </div>
              <div className="risk-bar-track">
                <div
                  className="risk-bar-fill"
                  style={{
                    width: `${r.risk.composite_risk}%`,
                    background: meta.color,
                  }}
                />
              </div>
              <div className="route-card-risk">Risk score: {r.risk.composite_risk}/100</div>
              <div className="route-card-detail">
                🚧 {r.damage_count} damage signals · 🔴 {r.blackspot_count} black spots
              </div>
              <details>
                <summary>Score breakdown</summary>
                <ul className="breakdown-list">
                  <li>Road damage: {r.risk.road_damage_score}/100</li>
                  <li>Accident risk: {r.risk.accident_score}/100</li>
                  <li>Personal safety: {r.risk.safety_score}/100</li>
                  <li>Time-of-day: {r.risk.time_of_day_score}/100</li>
                </ul>
              </details>
            </div>
          );
        })}
      </div>
    </div>
  );
}
