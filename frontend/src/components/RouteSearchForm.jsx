import React, { useState } from "react";

export default function RouteSearchForm({ onSearch, onStartPicking, origin, destination, loading }) {
  const [hour, setHour] = useState("");

  return (
    <div className="panel">
      <h2>Find a safe route</h2>

      <div className="pick-row">
        <button
          className={`pick-btn ${origin ? "picked" : ""}`}
          onClick={() => onStartPicking("origin")}
        >
          {origin ? `Origin: ${origin[0].toFixed(4)}, ${origin[1].toFixed(4)}` : "📍 Click map to set Origin"}
        </button>
        <button
          className={`pick-btn ${destination ? "picked" : ""}`}
          onClick={() => onStartPicking("destination")}
        >
          {destination
            ? `Destination: ${destination[0].toFixed(4)}, ${destination[1].toFixed(4)}`
            : "🏁 Click map to set Destination"}
        </button>
      </div>

      <label className="field">
        Departure hour (optional, 0-23 — affects night-time risk weighting)
        <input
          type="number"
          min="0"
          max="23"
          value={hour}
          onChange={(e) => setHour(e.target.value)}
          placeholder="Current time used if blank"
        />
      </label>

      <button
        className="primary-btn"
        disabled={!origin || !destination || loading}
        onClick={() =>
          onSearch({
            origin_lat: origin[0],
            origin_lng: origin[1],
            destination_lat: destination[0],
            destination_lng: destination[1],
            departure_hour: hour === "" ? null : parseInt(hour, 10),
          })
        }
      >
        {loading ? "Calculating…" : "Find Safe Routes"}
      </button>
    </div>
  );
}
