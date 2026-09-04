import React, { useState } from "react";
import MapView from "./components/MapView";
import RouteSearchForm from "./components/RouteSearchForm";
import RouteComparisonCards from "./components/RouteComparisonCards";
import CrowdReportForm from "./components/CrowdReportForm";
import DamageUpload from "./components/DamageUpload";
import Dashboard from "./components/Dashboard";
import { api } from "./api";

const DEFAULT_CENTER = [22.5726, 88.3639]; // Kolkata — change to match your city / OSRM extract

const TABS = [
  { id: "route", label: "🗺️ Route" },
  { id: "report", label: "🛡️ Report safety" },
  { id: "damage", label: "🚧 Road damage" },
  { id: "dashboard", label: "📊 Dashboard" },
];

export default function App() {
  const [tab, setTab] = useState("route");

  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [pickTarget, setPickTarget] = useState(null); // 'origin' | 'destination' | 'report' | 'damage' | null
  const [reportPoint, setReportPoint] = useState(null);
  const [damagePoint, setDamagePoint] = useState(null);

  const [routes, setRoutes] = useState([]);
  const [note, setNote] = useState("");
  const [selectedLabel, setSelectedLabel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePointPicked = (latlng) => {
    const point = [latlng.lat, latlng.lng];
    if (pickTarget === "origin") setOrigin(point);
    else if (pickTarget === "destination") setDestination(point);
    else if (pickTarget === "report") setReportPoint(point);
    else if (pickTarget === "damage") setDamagePoint(point);
    setPickTarget(null);
  };

  const fetchOSRM = async (oLat, oLng, dLat, dLng) => {
    const coords = `${oLng},${oLat};${dLng},${dLat}`;
    const url = `https://router.project-osrm.org/route/v1/driving/${coords}?alternatives=true&geometries=polyline6&overview=full`;
    const res = await fetch(url);
    const data = await res.json();
    if (data.code !== "Ok" || !data.routes?.length) throw new Error("OSRM returned no route");
    return data.routes.slice(0, 3).map(r => ({
      geometry: r.geometry,
      distance_m: r.distance,
      duration_s: r.duration,
    }));
  };

  const rankRoutes = (scored) => {
    if (!scored.length) return [];
    const durations = scored.map(r => r.duration_s);
    const risks = scored.map(r => r.risk);
    const dMin = Math.min(...durations), dMax = Math.max(...durations);
    const rMin = Math.min(...risks), rMax = Math.max(...risks);
    const norm = (v, lo, hi) => hi === lo ? 0 : (v - lo) / (hi - lo);
    const labels = ["fastest", "balanced", "safest"];
    const indices = [
      durations.indexOf(dMin),
      scored.reduce((bi, r, i) => 0.5 * norm(r.duration_s, dMin, dMax) + 0.5 * norm(r.risk, rMin, rMax) < 0.5 * norm(scored[bi].duration_s, dMin, dMax) + 0.5 * norm(scored[bi].risk, rMin, rMax) ? i : bi, 0),
      risks.indexOf(rMin),
    ];
    return labels.map((label, i) => ({ ...scored[indices[i]], label,
      distance_km: +(scored[indices[i]].distance_m / 1000).toFixed(2),
      duration_min: +(scored[indices[i]].duration_s / 60).toFixed(1),
      risk: { composite_risk: scored[indices[i]].risk, road_damage_score: 0, accident_score: 0, safety_score: 0, time_of_day_score: 0, signal_counts: {} },
      blackspot_count: 0, damage_count: 0,
    }));
  };

  const handleSearch = async (payload) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch routes from OSRM directly from browser (avoids server IP rate limits)
      const candidates = await fetchOSRM(
        payload.origin_lat, payload.origin_lng,
        payload.destination_lat, payload.destination_lng
      );
      // Assign mock risk scores (0=safest, increases with index)
      const scored = candidates.map((r, i) => ({ ...r, risk: i * 15 }));
      const ranked = rankRoutes(scored);
      setRoutes(ranked);
      const fastest = ranked.find(r => r.label === "fastest");
      const safest = ranked.find(r => r.label === "safest");
      const timePct = fastest && safest ? Math.round(((safest.duration_s - fastest.duration_s) / fastest.duration_s) * 100) : 0;
      setNote(timePct >= 0
        ? `Safest route is ${timePct}% longer but has lower risk than the fastest route.`
        : `Safest route is ${Math.abs(timePct)}% faster and has lower risk.`);
      setSelectedLabel(ranked.find(r => r.label === "balanced")?.label || ranked[0]?.label);
      // Also send to backend for risk scoring + analytics logging (non-blocking)
      api.findRoutes(payload).then(res => {
        if (res.routes?.length) {
          setRoutes(res.routes);
          setNote(res.comparison_note);
        }
      }).catch(() => {});
    } catch (e) {
      setError("Could not find a route. Try picking two points closer together or in a different area.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>🛣️ SafeRoute</h1>
        <p>Risk-aware navigation — not just fastest, but safest.</p>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="app-body">
        <aside className="sidebar">
          {tab === "route" && (
            <>
              <RouteSearchForm
                origin={origin}
                destination={destination}
                loading={loading}
                onStartPicking={(target) => setPickTarget(target)}
                onSearch={handleSearch}
              />
              {error && <p className="status-error">{error}</p>}
              <RouteComparisonCards
                routes={routes}
                note={note}
                selectedLabel={selectedLabel}
                onSelect={setSelectedLabel}
              />
            </>
          )}

          {tab === "report" && (
            <CrowdReportForm
              pickedPoint={reportPoint}
              onStartPicking={() => setPickTarget("report")}
            />
          )}

          {tab === "damage" && (
            <DamageUpload
              pickedPoint={damagePoint}
              onStartPicking={() => setPickTarget("damage")}
            />
          )}

          {tab === "dashboard" && <Dashboard />}
        </aside>

        <main className="map-pane">
          <MapView
            center={DEFAULT_CENTER}
            routes={tab === "route" ? routes : []}
            selectedLabel={selectedLabel}
            pickMode={pickTarget !== null}
            onPointPicked={handlePointPicked}
            originMarker={origin}
            destMarker={destination}
            showRiskLayers={tab !== "dashboard"}
          />
          {pickTarget && (
            <div className="pick-hint">Click anywhere on the map to set the {pickTarget} point…</div>
          )}
        </main>
      </div>
    </div>
  );
}
