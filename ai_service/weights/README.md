# Model weights

Put your trained YOLOv8 checkpoint here as `best.pt` after running
`app/train.py` (see that file for the full fine-tuning recipe).

Until `best.pt` exists, `ai_service` automatically falls back to a
clearly-labelled heuristic detector (`model_version: "heuristic-fallback-v0"`)
so the rest of the system remains fully demoable.

Do not commit large weight files to Git — add `*.pt` to `.gitignore`
and instead share weights via Google Drive / GitHub Releases / Git LFS,
and document the download step in your README.
