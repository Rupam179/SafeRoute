# SafeRoute — Viva / Examiner Prep

Anticipated questions and the strongest honest answer, grounded in what's
actually built. Adjust once you have real data/model numbers.

---

**Q: Isn't this just Google Maps?**
No — Google Maps optimises for time/distance. SafeRoute takes OSRM's
candidate routes and re-ranks them using a composite risk score built from
road-condition (AI-detected), accident history, and personal-safety
signals, then shows the explicit time-vs-risk trade-off. The routing
engine (OSRM) is a commodity component; the contribution is the risk
layer and ranking logic on top of it.

**Q: What's the actual AI/ML contribution?**
A YOLOv8 model fine-tuned on RDD2022 + our own locally-collected photos,
detecting road/bridge surface damage. Its output feeds directly into the
same risk-scoring pipeline as every other signal type — see
`backend/app/services/risk_engine.py`.

**Q: Why isn't the whole risk score itself a machine-learned model?**
Deliberate scope decision (documented in `docs/ARCHITECTURE.md` Section 5):
explainability, lack of labelled ground-truth for "route safety" to train
against, and keeping the ML contribution focused and well-posed (damage
detection) rather than diluted across an under-determined ranking model.

**Q: Where does your accident/crime data come from? Did you use police
records?**
No — explicitly out of scope. We use public, aggregate, area-level
statistics from MoRTH, NCRB, and data.gov.in. We never access FIR/General
Diary-level records, which are private and not appropriate for a student
project (see `docs/DATA_PIPELINE.md`).

**Q: How do you know your risk score is meaningful and not arbitrary?**
The weights (`backend/app/config.py`) are documented and tunable; each
sub-score is traceable to specific `risk_signals` rows retrievable via
`GET /api/risk-signals`; and the comparison sentence is generated from the
actual score delta, not a template. We evaluated it against 5-10 real
source-destination pairs in our city (see `docs/MODEL_EVALUATION.md`
Section 6) — we're not claiming statistical validation, but transparent,
inspectable behaviour.

**Q: What's your model's real accuracy?**
See `docs/MODEL_EVALUATION.md` — report the actual number. If it's below
your original 75% target, explain what you learned from the gap (lighting,
angle, dataset size) — this is a stronger answer than an inflated number.

**Q: Is this safety score a guarantee?**
No — we're explicit that SafeRoute provides an indicative risk score based
on available data, not a safety certification. Crowd-sourced coverage
especially will be sparse; we present it as a proof-of-concept signal, not
a validated metric.

**Q: How does this scale beyond your demo city?**
The `risk_signals` schema and scoring pipeline are city-agnostic — scaling
means (a) re-running `scripts/setup_osrm.sh` with a different OSM extract,
and (b) populating `risk_signals` for the new region via the same data
pipeline. No code changes required.

**Q: What would you build next if you had more time?**
Per the project's own scope boundaries: live-traffic rerouting, voice
navigation, an SOS system, a native offline mobile app, driver-behaviour
telematics, and full predictive-maintenance modelling — all deliberately
excluded to keep the core system achievable and well-tested within 8
months. Listed explicitly in the report's Future Work section.

**Q: Show me it actually working.**
Have 2-3 real source/destination pairs pre-tested in your city before the
demo. Walk through: pick points → route comparison cards appear → click
"Safest" → point out the risk breakdown → open the map risk layers →
submit a live crowd report → show it immediately affects a re-run route
query → open the dashboard tab.
