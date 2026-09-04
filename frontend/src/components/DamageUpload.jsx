import React, { useState } from "react";
import { api } from "../api";

export default function DamageUpload({ pickedPoint, onStartPicking }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    if (!file || !pickedPoint) {
      setError("Pick a location and choose an image first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.detectDamage(file, pickedPoint[0], pickedPoint[1]);
      setResult(res);
    } catch (e) {
      setError("Detection failed. Is ai_service running?");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <h2>Road damage detection</h2>
      <p className="muted">
        Upload a road/bridge photo. Detections are written straight into the
        risk engine as <code>road_damage</code> signals.
      </p>

      <button className="pick-btn" onClick={onStartPicking}>
        {pickedPoint
          ? `📍 ${pickedPoint[0].toFixed(4)}, ${pickedPoint[1].toFixed(4)}`
          : "📍 Pick photo location on map"}
      </button>

      <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />

      <button className="primary-btn" onClick={submit} disabled={busy}>
        {busy ? "Analysing…" : "Run damage detection"}
      </button>

      {error && <p className="status-error">{error}</p>}

      {result && (
        <div className="damage-result">
          <p>
            Model: <strong>{result.model_version}</strong>
            {result.model_version.startsWith("heuristic") && (
              <span className="badge-warn"> (placeholder — swap in trained weights)</span>
            )}
          </p>
          {result.detections.length === 0 ? (
            <p>No damage detected in this image.</p>
          ) : (
            <ul>
              {result.detections.map((d, i) => (
                <li key={i}>
                  {d.class.replace(/_/g, " ")} — confidence {(d.confidence * 100).toFixed(0)}%
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
