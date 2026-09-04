import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "";

const client = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 20000,
});

export const api = {
  findRoutes: (payload) => client.post("/routes", payload).then((r) => r.data),

  getRiskSignals: (params = {}) =>
    client.get("/risk-signals", { params }).then((r) => r.data),

  submitCrowdReport: (payload) =>
    client.post("/crowd-reports", payload).then((r) => r.data),

  listCrowdReports: () => client.get("/crowd-reports").then((r) => r.data),

  getAnalyticsSummary: () => client.get("/analytics/summary").then((r) => r.data),

  getRiskByArea: () => client.get("/analytics/risk-by-area").then((r) => r.data),

  detectDamage: (file, lat, lng) => {
    const form = new FormData();
    form.append("file", file);
    form.append("lat", lat);
    form.append("lng", lng);
    return client
      .post("/damage-detection", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
};
