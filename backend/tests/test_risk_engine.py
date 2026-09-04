"""
Unit tests for risk_engine's pure functions (ranking + comparison note).
The DB-dependent function (score_route) is exercised via integration tests
against a real Postgres/PostGIS instance — see docs/API.md for how to run
those with docker compose.
"""
from app.services.risk_engine import rank_routes, build_comparison_note


def make_route(duration_s, composite_risk):
    return {
        "geometry": "mock",
        "distance_m": duration_s * 10,
        "duration_s": duration_s,
        "risk": {
            "road_damage_score": 0, "accident_score": 0,
            "safety_score": 0, "time_of_day_score": 0,
            "composite_risk": composite_risk,
            "signal_counts": {},
            "_blackspot_count": 0, "_damage_count": 0,
        },
    }


def test_rank_routes_picks_correct_fastest_and_safest():
    routes = [
        make_route(duration_s=1500, composite_risk=78),   # fastest, risky
        make_route(duration_s=1740, composite_risk=48),   # balanced
        make_route(duration_s=1980, composite_risk=25),   # safest, slowest
    ]
    labeled = rank_routes(routes)
    by_label = {r["label"]: r for r in labeled}

    assert by_label["fastest"]["duration_s"] == 1500
    assert by_label["safest"]["risk"]["composite_risk"] == 25
    assert by_label["balanced"]["duration_s"] == 1740


def test_rank_routes_handles_single_route():
    routes = [make_route(duration_s=1000, composite_risk=40)]
    labeled = rank_routes(routes)
    assert len(labeled) == 3
    assert all(r["duration_s"] == 1000 for r in labeled)


def test_comparison_note_reports_tradeoff():
    routes = [
        make_route(duration_s=1500, composite_risk=80),
        make_route(duration_s=1650, composite_risk=48),
    ]
    labeled = rank_routes(routes)
    note = build_comparison_note(labeled)
    assert "longer" in note or "faster" in note
    assert "%" in note


def test_comparison_note_single_route():
    routes = [make_route(duration_s=1000, composite_risk=40)]
    labeled = rank_routes(routes)
    note = build_comparison_note(labeled)
    assert "Only one distinct route" in note
