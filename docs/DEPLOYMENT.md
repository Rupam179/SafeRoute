# SafeRoute — Deployment Guide

Your project's success metrics explicitly require a **publicly accessible
URL**, not just localhost. Three practical paths, cheapest first.

## Option A — Single VPS with Docker Compose (recommended for this project)

Works well because everything (backend, ai_service, OSRM, Postgres) is
already containerised and networked via `docker-compose.yml`.

1. Get a small VPS (e.g. a ₹1,500–2,500/month tier, or a student credit
   program — DigitalOcean/AWS/GCP/Azure all run student programs).
   2 vCPU / 4GB RAM is comfortable; OSRM's memory use depends on region size.
2. Install Docker + Docker Compose on the VPS.
3. Clone your repo, copy `.env.example` → `.env`, set a real `SECRET_KEY`.
4. Run `bash scripts/setup_osrm.sh` on the VPS (or prepare `osrm-data/`
   locally and `scp` it over — extraction is CPU-heavy, cheaper to do once).
5. `docker compose up --build -d`
6. Point a domain (or use the VPS's IP) at the `frontend` service's port
   (80 inside the container → map it to 80/443 on the host, or put nginx/
   Caddy in front for automatic HTTPS via Let's Encrypt).
7. Open firewall for 80/443 only — keep 8000/8500/5432/5001 internal to
   the Docker network (already the case; only `frontend`'s port needs to
   be public-facing in production — adjust `docker-compose.yml`'s exposed
   ports accordingly before going live).

## Option B — Render / Railway (free tier, simpler, some limitations)

- Deploy `backend/` and `ai_service/` as separate **Web Services** (each
  has its own Dockerfile already).
- Deploy `frontend/` as a **Static Site** (build command `npm run build`,
  publish directory `dist`) — point its `/api` calls at your backend's
  public Render/Railway URL instead of the nginx proxy (edit
  `vite.config.js`'s proxy target or use an env-driven `baseURL` in `api.js`
  for production builds).
- Use Render/Railway's managed Postgres add-on — enable the PostGIS
  extension via a one-time `CREATE EXTENSION postgis;` (their dashboards
  usually allow running init SQL, or connect with `psql` once and run
  `db/init.sql` yourself).
- **OSRM is the tricky part on free tiers** — it needs real memory for
  the region file and isn't a typical "web service" workload. Options:
  - Self-host OSRM on a small always-on VPS just for that one service,
    and point `OSRM_BASE_URL` at it from your Render/Railway backend.
  - Or use a small enough city extract that it fits comfortably.

## Option C — All Docker Compose on a single free-tier cloud VM

Some student cloud credits (GCP/AWS/Azure/Oracle free tier VMs) give you
a full VM you can treat exactly like Option A.

---

## Checklist before your demo day

- [ ] `docker compose ps` shows all 5 services healthy
- [ ] `curl https://yourdomain/api/analytics/summary` returns real data
- [ ] Route search works for at least 5 real source-destination pairs in
      your target city (project plan Section 10 evaluation requirement)
- [ ] HTTPS is set up (Let's Encrypt via Caddy/nginx-certbot) — plain HTTP
      demo links look unfinished
- [ ] `SECRET_KEY` in `.env` is a real random value, not the placeholder
- [ ] Basic logging is in place so you can debug a mid-demo failure fast
      (`docker compose logs -f backend`)
