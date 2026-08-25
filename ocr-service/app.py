"""
SNAPTOCK OCR service.

    POST /ocr/nota   multipart image -> validated line items
    GET  /health     readiness

Set MOCK=1 to serve a fixture with no model and no paddle installed.
"""

from __future__ import annotations

import io
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from pipeline import assemble

MOCK = os.environ.get("MOCK", "0") == "1"
# Where the fine-tuned recognizer comes from. The weights are 114 MB, which is
# past GitHub's file limit, so the repository does not carry them: a clone
# fetches them from the Hub on first start and the Hub's cache keeps them.
# MODEL_DIR still wins when it points at a real export, which is what makes a
# locally trained model testable without publishing it first.
HF_REPO = os.environ.get("HF_REPO", "nafisN14/snaptock")
HF_REVISION = os.environ.get("HF_REVISION", "main")
MODEL_DIR = os.environ.get("MODEL_DIR", "models/rec")
REC_MODEL = os.environ.get("REC_MODEL_NAME", "PP-OCRv5_mobile_rec")
DET_MODEL = os.environ.get("DET_MODEL_NAME", "PP-OCRv5_mobile_det")
# The detector shrinks the long side to this before looking. Raising it opens
# up the gaps between handwritten cells on big phone photos and stops the
# detector welding neighbours into one line -- but measured across 40 receipts
# it costs more than it wins (89.3% of rows reconcile at 960, 84.8% at 1600),
# so the default stands and this is here to be tuned per corpus.
DET_SIDE_LEN = int(os.environ.get("DET_SIDE_LEN", 960))
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 12 * 1024 * 1024))

FIXTURE = Path(__file__).parent / "fixtures" / "sample_response.json"
# The three files PaddleOCR needs to load an exported recognizer. Named
# explicitly rather than pulling the whole repo, so an unrelated file added to
# the Hub later cannot change what this service loads.
WEIGHTS = ("inference.json", "inference.pdiparams", "inference.yml")
models: dict = {}


def resolve_model_dir() -> str:
    """Local export if there is one, otherwise fetch it from the Hub.

    A partly-downloaded directory is treated as absent: loading half an export
    fails deep inside Paddle with an error that says nothing about the cause.
    """
    local = Path(MODEL_DIR)
    if all((local / name).is_file() for name in WEIGHTS):
        print(f"using local weights at {local}")
        return str(local)

    from huggingface_hub import snapshot_download

    print(f"fetching weights from {HF_REPO}@{HF_REVISION} (114 MB, once) ...")
    path = snapshot_download(repo_id=HF_REPO, revision=HF_REVISION,
                             allow_patterns=list(WEIGHTS))
    missing = [n for n in WEIGHTS if not (Path(path) / n).is_file()]
    if missing:
        raise RuntimeError(
            f"{HF_REPO} is missing {', '.join(missing)}. The recognizer needs "
            f"all of {', '.join(WEIGHTS)} exported together."
        )
    print(f"weights ready at {path}")
    return path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load once at startup; loading per request would dominate latency."""
    if MOCK:
        print("MOCK=1 - serving fixtures, no model loaded")
    else:
        from paddleocr import TextDetection, TextRecognition
        model_dir = resolve_model_dir()
        models["det"] = TextDetection(model_name=DET_MODEL,
                                      limit_side_len=DET_SIDE_LEN)
        # model_name is required: TextRecognition validates the directory's
        # config against its default (PP-OCRv6) and would reject our v5 export.
        models["rec"] = TextRecognition(model_name=REC_MODEL, model_dir=model_dir)
        print("models ready")
    yield
    models.clear()


app = FastAPI(title="SNAPTOCK OCR", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "mock": MOCK, "models_loaded": sorted(models)}


@app.post("/ocr/nota")
async def ocr_nota(image: UploadFile = File(...)):
    started = time.perf_counter()
    raw = await image.read()

    if not raw:
        raise HTTPException(400, detail={"error": "empty_upload"})
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, detail={"error": "file_too_large",
                                         "max_bytes": MAX_BYTES})

    if MOCK:
        body = json.loads(FIXTURE.read_text())
        body["ms"] = int((time.perf_counter() - started) * 1000)
        return JSONResponse(body)

    try:
        page = np.array(Image.open(io.BytesIO(raw)).convert("RGB"))
    except Exception:
        raise HTTPException(415, detail={"error": "unreadable_image"})

    # PaddleOCR accepts numpy arrays or paths only - it silently ignores PIL
    # images and returns nothing, so everything below stays numpy.
    # cv2 arrives with paddle, and MOCK=1 has already returned above.
    from geometry import bounds, deskew, rectify, upright

    def detect(img):
        found = models["det"].predict(img)
        return list(found[0]["dt_polys"]) if found else []

    def recognize(patches):
        return list(models["rec"].predict(patches))

    polys = detect(page)
    # Level the page and turn it the right way up before reading it: the
    # recognizer only reads horizontal text, and a photo of a nota is often
    # neither level nor upright.
    page, polys, _ = deskew(page, polys, detect)
    page, polys = upright(page, polys, recognize)

    crops, geometry = [], []
    for poly in polys:
        patch = rectify(page, poly)
        if patch is not None:
            crops.append(patch)
            geometry.append(bounds(poly))

    if not crops:
        raise HTTPException(422, detail={"error": "no_text_detected"})

    boxes = [
        {**box,
         "text": (pred.get("rec_text") or "").strip(),
         "conf": float(pred.get("rec_score") or 0.0)}
        for box, pred in zip(geometry, recognize(crops))
    ]

    height, width = page.shape[:2]
    body = assemble([b for b in boxes if b["text"]], width, height)
    body["ms"] = int((time.perf_counter() - started) * 1000)
    return JSONResponse(body)
