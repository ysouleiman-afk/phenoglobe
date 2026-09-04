"""
PhenoGlobe backend (FastAPI). The analysis itself lives in pipeline.py.

POST /analyze  (multipart: photo1, photo2)  -> population breakdown + country heat map
GET  /         -> frontend

Run:  .venv/Scripts/python -m uvicorn main:app --port 8000
"""
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import pipeline

BASE = Path(__file__).parent
STATIC = BASE / "static"

app = FastAPI(title="PhenoGlobe")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/health")
def health():
    return {"ok": True, **pipeline.status()}


@app.post("/analyze")
async def analyze(photo1: UploadFile = File(...), photo2: UploadFile = File(...)):
    tmpdir = Path(tempfile.mkdtemp(prefix="phenoglobe_"))
    try:
        paths, names = [], []
        for upload in (photo1, photo2):
            suffix = Path(upload.filename or "img.jpg").suffix or ".jpg"
            dest = tmpdir / f"{uuid.uuid4().hex}{suffix}"
            with dest.open("wb") as fh:
                shutil.copyfileobj(upload.file, fh)
            paths.append(str(dest))
            names.append(upload.filename or "photo")
        try:
            return pipeline.analyze_paths(paths, names)
        except pipeline.AnalysisError as exc:
            raise HTTPException(exc.status, str(exc))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
