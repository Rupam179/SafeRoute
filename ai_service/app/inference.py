"""
Road-damage inference wrapper.

Design goal: the rest of the system (backend, frontend, demo) should never
care whether a *real* trained YOLOv8 model is loaded or not. This module
exposes one function, `predict(image_bytes) -> dict`, and picks the best
available backend automatically:

  1. If `weights/best.pt` exists AND `ultralytics` is installed -> real
     YOLOv8 inference (this is what you'll have after Phase 5/6 of the
     project plan, once you've fine-tuned on RDD2022 + your own photos).
  2. Otherwise -> a deterministic heuristic fallback based on simple image
     statistics (edge density / dark-blob detection). This is NOT a real
     damage detector — it exists purely so the full pipeline (upload ->
     detection -> risk_signal -> route risk) is demonstrable end-to-end
     before your trained model is ready. It is clearly labelled as such
     in every response (`model_version: "heuristic-fallback-v0"`), and you
     should be upfront about this distinction in your report and viva.

To go live with your real model:
    1. Train with train.py (see that file for the full YOLOv8 recipe).
    2. Copy the resulting best.pt into ai_service/weights/best.pt
    3. Restart the ai_service container. That's it — no code changes needed.
"""
from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image, ImageFilter

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "..", "weights", "best.pt")
MODEL_VERSION_REAL = "yolov8-roaddamage-v1"
MODEL_VERSION_FALLBACK = "heuristic-fallback-v0"

CLASS_NAMES = ["longitudinal_crack", "transverse_crack", "alligator_crack", "pothole", "rutting"]

_yolo_model = None
_yolo_load_attempted = False


def _try_load_yolo():
    global _yolo_model, _yolo_load_attempted
    if _yolo_load_attempted:
        return _yolo_model
    _yolo_load_attempted = True

    if not os.path.exists(WEIGHTS_PATH):
        return None
    try:
        from ultralytics import YOLO  # noqa: import only if available
        _yolo_model = YOLO(WEIGHTS_PATH)
        return _yolo_model
    except ImportError:
        return None


def _heuristic_predict(image: Image.Image) -> list[dict]:
    """
    Deterministic, non-ML placeholder: flags "damage" based on dark, high-
    edge-density regions (potholes/cracks tend to be dark and irregular in
    photos). Bounded, seeded by pixel content so results are reproducible.
    Replace this entirely once your trained model is in place — this
    function's only job is to keep the API contract identical either way.
    """
    gray = image.convert("L").resize((256, 256))
    edges = gray.filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(edges, dtype=np.float32)

    edge_density = float(arr.mean()) / 255.0
    dark_ratio = float((np.asarray(gray) < 80).mean())

    detections = []
    if edge_density > 0.08 and dark_ratio > 0.03:
        # crude "how many distinct damage regions" proxy
        n_detections = 1 + int(min(3, edge_density * 10))
        for i in range(n_detections):
            cls_idx = int((edge_density * 97 + dark_ratio * 53 + i) * 7) % len(CLASS_NAMES)
            confidence = round(min(0.95, 0.4 + edge_density + dark_ratio), 2)
            detections.append({
                "class": CLASS_NAMES[cls_idx],
                "confidence": confidence,
                "bbox_norm": None,  # heuristic mode doesn't localise a real box
            })
    return detections


def _yolo_predict(model, image: Image.Image) -> list[dict]:
    results = model.predict(image, verbose=False)
    detections = []
    for r in results:
        names = r.names
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            xyxyn = box.xyxyn[0].tolist()  # normalised [x1, y1, x2, y2]
            detections.append({
                "class": names.get(cls_id, str(cls_id)),
                "confidence": round(conf, 3),
                "bbox_norm": [round(v, 4) for v in xyxyn],
            })
    return detections


def predict(image_bytes: bytes) -> dict:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    model = _try_load_yolo()
    if model is not None:
        detections = _yolo_predict(model, image)
        version = MODEL_VERSION_REAL
    else:
        detections = _heuristic_predict(image)
        version = MODEL_VERSION_FALLBACK

    return {"model_version": version, "detections": detections}
