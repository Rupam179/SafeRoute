from fastapi import FastAPI, File, HTTPException, UploadFile

from app.inference import predict, WEIGHTS_PATH
import os

app = FastAPI(title="SafeRoute AI Service", version="1.0.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "saferoute-ai-service",
        "real_weights_loaded": os.path.exists(WEIGHTS_PATH),
    }


@app.post("/predict")
async def predict_endpoint(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        result = predict(image_bytes)
    except Exception as e:  # noqa: broad — surfaces cleanly to the caller
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    return result
