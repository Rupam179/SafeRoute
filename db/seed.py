"""
SafeRoute — Development Seed Script
====================================

Populates risk_signals with REALISTIC PLACEHOLDER data around a chosen city
centre, so your team has something to route through and demo on day one —
before the real MoRTH/NCRB/data.gov.in pipelines and the trained YOLOv8
model are ready.

IMPORTANT — read this before your viva:
This script generates SYNTHETIC data (randomly scattered points with
plausible severities). It is clearly labelled `source='synthetic_seed'` in
the database so it can never be confused with real public data. Replace it
with your real data pipeline (see docs/DATA_PIPELINE.md) well before your
evaluation — the project's success metrics explicitly require real,
citable public data sources.

Usage:
    python seed.py --city kolkata --n-blackspots 40 --n-damage 60 --n-crowd 30

Requires: pip install psycopg2-binary
Reads DATABASE_URL from env, default matches docker-compose.
"""
import argparse
import math
import os
import random

import psycopg2

CITY_CENTERS = {
    "kolkata": (22.5726, 88.3639),
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "pune": (18.5204, 73.8567),
}

DAMAGE_CLASSES = ["pothole", "alligator_crack", "longitudinal_crack", "rutting"]


def random_point_near(lat, lng, radius_km=8.0):
    """Uniform-ish random point within radius_km of a centre — fine for demo data."""
    radius_deg = radius_km / 111.0  # rough km->degrees
    r = radius_deg * (random.random() ** 0.5)
    theta = random.random() * 2 * math.pi
    return lat + r * math.sin(theta), lng + r * math.cos(theta)


def seed(conn, city, n_blackspots, n_damage, n_crowd, n_lighting):
    lat0, lng0 = CITY_CENTERS[city]
    cur = conn.cursor()

    print(f"Seeding synthetic data around {city} ({lat0}, {lng0})...")

    for _ in range(n_blackspots):
        lat, lng = random_point_near(lat0, lng0)
        severity = random.choices([2, 3, 4, 5], weights=[2, 3, 3, 1])[0]
        cur.execute("""
            INSERT INTO risk_signals (geom, type, severity, source, meta)
            VALUES (ST_MakePoint(%s, %s)::geography, 'accident_blackspot', %s, 'synthetic_seed',
                    %s::jsonb)
        """, (lng, lat, severity, '{"note": "placeholder — replace with MoRTH/NCRB/data.gov.in data"}'))

    for _ in range(n_damage):
        lat, lng = random_point_near(lat0, lng0)
        severity = random.choices([1, 2, 3, 4], weights=[3, 3, 2, 1])[0]
        cls = random.choice(DAMAGE_CLASSES)
        cur.execute("""
            INSERT INTO risk_signals (geom, type, severity, source, meta)
            VALUES (ST_MakePoint(%s, %s)::geography, 'road_damage', %s, 'synthetic_seed',
                    %s::jsonb)
        """, (lng, lat, severity, f'{{"damage_class": "{cls}", "confidence": 0.5}}'))

    for _ in range(n_crowd):
        lat, lng = random_point_near(lat0, lng0)
        severity = random.choices([1, 2, 3, 4], weights=[3, 3, 2, 1])[0]
        lighting = random.choice(["good", "moderate", "poor"])
        cur.execute("""
            INSERT INTO risk_signals (geom, type, severity, source, time_of_day, meta)
            VALUES (ST_MakePoint(%s, %s)::geography, 'crowd_safety_report', %s, 'synthetic_seed',
                    %s, %s::jsonb)
        """, (lng, lat, severity, random.choice(["day", "night"]), f'{{"lighting": "{lighting}"}}'))

    for _ in range(n_lighting):
        lat, lng = random_point_near(lat0, lng0)
        severity = random.choices([1, 2, 3], weights=[2, 3, 2])[0]
        lighting = random.choice(["poor", "moderate"])
        cur.execute("""
            INSERT INTO risk_signals (geom, type, severity, source, meta)
            VALUES (ST_MakePoint(%s, %s)::geography, 'lighting', %s, 'synthetic_seed',
                    %s::jsonb)
        """, (lng, lat, severity, f'{{"lighting": "{lighting}"}}'))

    conn.commit()
    print(f"Done: {n_blackspots} blackspots, {n_damage} road_damage, "
          f"{n_crowd} crowd_safety_report, {n_lighting} lighting signals inserted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", choices=list(CITY_CENTERS.keys()), default="kolkata")
    parser.add_argument("--n-blackspots", type=int, default=40)
    parser.add_argument("--n-damage", type=int, default=60)
    parser.add_argument("--n-crowd", type=int, default=30)
    parser.add_argument("--n-lighting", type=int, default=25)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "postgresql://saferoute:saferoute@localhost:5432/saferoute"),
    )
    args = parser.parse_args()

    connection = psycopg2.connect(args.database_url)
    seed(connection, args.city, args.n_blackspots, args.n_damage, args.n_crowd, args.n_lighting)
    connection.close()
