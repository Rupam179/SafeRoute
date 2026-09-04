# SafeRoute — Model Evaluation

Fill this in with your **real** numbers once `ai_service/app/train.py` has
been run against your dataset. Report actual results, including weak ones
— the project's own success metric is "report the real number, whatever
it is," and honest limitations discussion is explicitly part of grading.

## 1. Dataset

| Split | Source | Count |
|---|---|---|
| Train | RDD2022 subset | _fill in_ |
| Val | RDD2022 subset | _fill in_ |
| Test (held out, never trained on) | Your own collected photos | _fill in, target 150-300_ |

## 2. Training configuration

- Base model: `yolov8n.pt` / `yolov8s.pt` (_choose based on your compute_)
- Epochs: _fill in_
- Image size: _fill in_
- Augmentation: _default Ultralytics augmentation / list any changes_

## 3. Results on held-out test set (your own local photos)

| Metric | Value |
|---|---|
| Precision | _fill in_ |
| Recall | _fill in_ |
| mAP50 | _fill in_ |
| mAP50-95 | _fill in_ |

Compare against the zero-shot / pretrained-only baseline if time permits:

| | Precision | Recall | mAP50 |
|---|---|---|---|
| Zero-shot (no fine-tuning) | | | |
| Fine-tuned (yours) | | | |

## 4. Per-class breakdown

| Class | Precision | Recall | Notes |
|---|---|---|---|
| pothole | | | |
| longitudinal_crack | | | |
| transverse_crack | | | |
| alligator_crack | | | |
| rutting | | | |

## 5. Honest limitations

Document real, observed failure modes — this is a strength, not a
weakness, in your report:
- Lighting conditions where the model underperforms (e.g. glare, dusk)
- Camera angle sensitivity
- Confusions between damage classes
- Performance gap between RDD2022 test images and your own local photos
  (if any — this is the whole point of holding out local photos)

## 6. Composite risk-score sanity check

For 5–10 real source-destination pairs in your target city (project plan
Section 10), record the fastest-vs-safest trade-off your deployed system
actually returned:

| Route | Fastest time | Safest time | Δ time | Fastest risk | Safest risk | Δ risk |
|---|---|---|---|---|---|---|
| A → B | | | | | | |
| C → D | | | | | | |
