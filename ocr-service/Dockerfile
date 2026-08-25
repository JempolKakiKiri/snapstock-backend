FROM python:3.10-slim

# opencv (pulled in by paddleocr) needs these at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir paddlepaddle==3.0.0 paddleocr==3.7.0

COPY app.py geometry.py layout.py pipeline.py ./
COPY fixtures ./fixtures

# The fine-tuned recognizer is not in the image and not in git -- 114 MB is past
# GitHub's file limit. It is pulled from the Hub the first time the container
# starts and kept in the HF cache, which docker-compose.yml mounts as a named
# volume so a restart does not download it again.
#
# MODEL_DIR is left pointing at a path that does not exist in the image on
# purpose: if you bake weights in with `COPY models/rec /app/models/rec`, they
# are found and the download is skipped, with no other change.
ENV MODEL_DIR=/app/models/rec \
    HF_REPO=nafisN14/snaptock \
    HF_HOME=/app/.cache/huggingface \
    REC_MODEL_NAME=PP-OCRv5_mobile_rec \
    MOCK=0

EXPOSE 8001
# First start downloads 114 MB before the models load, so the grace period has
# to cover the download, not just the load.
HEALTHCHECK --interval=30s --timeout=5s --start-period=300s \
    CMD curl -fsS http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
