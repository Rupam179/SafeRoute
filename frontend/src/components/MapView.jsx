import React, { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  useMapEvents,
} from "react-leaflet";
import polyline from "polyline";
import { api } from "../api";

const RISK_COLORS = {
  accident_blackspot: "#e63946",
  road_damage: "#f4a261",
  crowd_safety_report: "#9d4edd",
  lighting: "#2a9d8f",
  crime_stat: "#e63946",
  poi_density: "#457b9d",
};

const ROUTE_COLORS = {
  fastest: "#3a86ff",
  balanced: "#ffb703",
  safest: "#2a9d8f",
};

function ClickCapture({ onPick }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng);
    },
  });
  return null;
}

export default function MapView({
  center,
  routes,
  selectedLabel,
  pickMode,
  onPointPicked,
  originMarker,
  destMarker,
  showRiskLayers,
}) {
  const [signals, setSignals] = useState([]);

  useEffect(() => {
    if (!showRiskLayers) return;
    api.getRiskSignals({ limit: 1500 }).then(setSignals).catch(() => {});
  }, [showRiskLayers]);

  return (
    <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {pickMode && <ClickCapture onPick={onPointPicked} />}

      {originMarker && <Marker position={originMarker}><Popup>Origin</Popup></Marker>}
      {destMarker && <Marker position={destMarker}><Popup>Destination</Popup></Marker>}

      {showRiskLayers &&
        signals.map((s) => (
          <CircleMarker
            key={`${s.type}-${s.id}`}
            center={[s.lat, s.lng]}
            radius={3 + s.severity}
            pathOptions={{
              color: RISK_COLORS[s.type] || "#888",
              fillOpacity: 0.6,
            }}
          >
            <Popup>
              <strong>{s.type.replace(/_/g, " ")}</strong>
              <br />
              Severity: {s.severity}/5
              <br />
              Source: {s.source}
            </Popup>
          </CircleMarker>
        ))}

      {routes.map((r) => {
        const points = polyline.decode(r.geometry, 6);
        const isSelected = r.label === selectedLabel;
        return (
          <Polyline
            key={r.label}
            positions={points}
            pathOptions={{
              color: ROUTE_COLORS[r.label],
              weight: isSelected ? 7 : 4,
              opacity: isSelected ? 0.95 : 0.45,
            }}
          />
        );
      })}
    </MapContainer>
  );
}
