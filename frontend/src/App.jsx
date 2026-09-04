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

  const handleSearch = async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.findRoutes(payload);
      setRoutes(res.routes);
      setNote(res.comparison_note);
      setSelectedLabel(res.routes.find((r) => r.label === "balanced")?.label || res.routes[0]?.label);
    } catch (e) {
      setError(
        e?.response?.data?.detail ||
          "Could not find a route. Check that OSRM is running and covers this area."
      );
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
