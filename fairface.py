"""
FairFace (ResNet-34, "fair_align_multi_7") inference via ONNX Runtime.

Outputs 18 logits: 7 race + 2 gender + 9 age buckets.
Race order (from the FairFace repo): White, Black, Latino_Hispanic, East Asian,
Southeast Asian, Indian, Middle Eastern.
"""
from pathlib import Path

import numpy as np

MODEL = Path(__file__).parent / "models" / "fairface.onnx"
RACES = ["White", "Black", "Latino_Hispanic", "East Asian", "Southeast Asian", "Indian", "Middle Eastern"]
GENDERS = ["Male", "Female"]
AGES = ["0-2", "3-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]
AGE_MID = [1, 6, 15, 25, 35, 45, 55, 65, 75]

# Map FairFace classes onto the app's phenotype buckets (phenotypes.CATEGORIES).
TO_BUCKET = {
    "White": "white", "Black": "black", "Latino_Hispanic": "latino hispanic",
    "East Asian": "asian", "Southeast Asian": "southeast asian",
    "Indian": "indian", "Middle Eastern": "middle eastern",
}

_session = None


def available() -> bool:
    if not MODEL.exists() or MODEL.stat().st_size < 50_000_000:
        return False
    try:
        import onnxruntime  # noqa: F401
        return True
    except ImportError:
        return False


def session():
    global _session
    if _session is None:
        import onnxruntime as ort
        _session = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
    return _session


def _softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def preprocess(face_rgb: np.ndarray) -> np.ndarray:
    """face_rgb: HxWx3 uint8 RGB crop (already aligned/cropped around the face)."""
    import cv2
    img = cv2.resize(face_rgb, (224, 224), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    img = (img - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array([0.229, 0.224, 0.225], dtype=np.float32)
    return img.transpose(2, 0, 1)[None]  # NCHW


def predict(face_rgb: np.ndarray) -> dict:
    sess = session()
    inp = sess.get_inputs()[0].name
    out = sess.run(None, {inp: preprocess(face_rgb)})[0][0]
    race = _softmax(out[:7]); gender = _softmax(out[7:9]); age = _softmax(out[9:18])
    return {
        "race": {r: float(p) for r, p in zip(RACES, race)},
        "buckets": {TO_BUCKET[r]: float(p) for r, p in zip(RACES, race)},
        "gender": GENDERS[int(gender.argmax())],
        "age": float(sum(p * m for p, m in zip(age, AGE_MID))),
    }


def crop_with_margin(img_rgb: np.ndarray, region: dict, margin: float = 0.25) -> np.ndarray:
    """FairFace was trained on crops with padding around the detected face box."""
    h, w = img_rgb.shape[:2]
    x, y, bw, bh = region["x"], region["y"], region["w"], region["h"]
    mx, my = int(bw * margin), int(bh * margin)
    x0, y0 = max(0, x - mx), max(0, y - my)
    x1, y1 = min(w, x + bw + mx), min(h, y + bh + my)
    return img_rgb[y0:y1, x0:x1]
