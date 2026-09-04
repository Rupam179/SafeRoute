import React, { useState } from "react";
import { api } from "../api";

export default function CrowdReportForm({ pickedPoint, onStartPicking }) {
  const [lighting, setLighting] = useState("unknown");
  const [activity, setActivity] = useState("unknown");
  const [incident, setIncident] = useState(false);
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState(null);

  const submit = async () => {
    if (!pickedPoint) {
      setStatus({ ok: false, msg: "Click 'Pick location on map' first." });
      return;
    }
    try {
      await api.submitCrowdReport({
        lat: pickedPoint[0],
        lng: pickedPoint[1],
        lighting,
        activity_level: activity,
        incident_report: incident,
        notes: notes || null,
      });
      setStatus({ ok: true, msg: "Thanks — your report now feeds the risk engine immediately." });
      setNotes("");
      setIncident(false);
    } catch (e) {
      setStatus({ ok: false, msg: "Could not submit report. Is the backend running?" });
    }
  };

  return (
    <div className="panel">
      <h2>Report a safety observation</h2>
      <p className="muted">
        Anonymous. Your report is immediately converted into a risk signal and
        used in route scoring — no waiting for moderation.
      </p>

      <button className="pick-btn" onClick={onStartPicking}>
        {pickedPoint
          ? `📍 ${pickedPoint[0].toFixed(4)}, ${pickedPoint[1].toFixed(4)}`
          : "📍 Pick location on map"}
      </button>

      <label className="field">
        Lighting
        <select value={lighting} onChange={(e) => setLighting(e.target.value)}>
          <option value="unknown">Not sure</option>
          <option value="good">Good</option>
          <option value="moderate">Moderate</option>
          <option value="poor">Poor</option>
        </select>
      </label>

      <label className="field">
        Foot traffic / activity
        <select value={activity} onChange={(e) => setActivity(e.target.value)}>
          <option value="unknown">Not sure</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </label>

      <label className="checkbox-field">
        <input type="checkbox" checked={incident} onChange={(e) => setIncident(e.target.checked)} />
        I want to report an incident here
      </label>

      <label className="field">
        Notes (optional)
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      </label>

      <button className="primary-btn" onClick={submit}>
        Submit report
      </button>

      {status && (
        <p className={status.ok ? "status-ok" : "status-error"}>{status.msg}</p>
      )}
    </div>
  );
}
