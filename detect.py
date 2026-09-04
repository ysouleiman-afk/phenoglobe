"""
Face detection + alignment with OpenCV's YuNet (tiny ONNX model, 5 landmarks).
Returns aligned RGB crops ready for the classifiers.
"""
from pathlib import Path

import cv2
import numpy as np

MODEL = Path(__file__).parent / "models" / "yunet.onnx"
_det = None


def detector(w, h):
    global _det
    if _det is None:
        _det = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), score_threshold=0.6, nms_threshold=0.3, top_k=50)
    _det.setInputSize((w, h))
    return _det


def load_rgb(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("unreadable image")
    # keep detection fast on huge phone photos
    h, w = img.shape[:2]
    scale = 1600 / max(h, w)
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def detect(img_rgb: np.ndarray) -> list[dict]:
    """Faces sorted by area, largest first. Each: box (x,y,w,h), score, eyes (l, r) in pixel coords."""
    h, w = img_rgb.shape[:2]
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    _, faces = detector(w, h).detect(bgr)
    out = []
    for f in (faces if faces is not None else []):
        x, y, bw, bh = [int(v) for v in f[:4]]
        out.append({
            "box": (max(0, x), max(0, y), bw, bh), "score": float(f[14]),
            "eyes": ((float(f[4]), float(f[5])), (float(f[6]), float(f[7]))),
            "nose": (float(f[8]), float(f[9])),
            "mouth": ((float(f[10]), float(f[11])), (float(f[12]), float(f[13]))),
        })
    out.sort(key=lambda d: d["box"][2] * d["box"][3], reverse=True)
    return out


def align_crop(img_rgb: np.ndarray, face: dict, margin: float = 0.25, size: int = 224) -> np.ndarray:
    """Rotate so the eyes are level (as FairFace's dlib alignment did), then crop the box + margin."""
    (lx, ly), (rx, ry) = face["eyes"]
    angle = np.degrees(np.arctan2(ry - ly, rx - lx))
    cx, cy = (lx + rx) / 2, (ly + ry) / 2
    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    h, w = img_rgb.shape[:2]
    rotated = cv2.warpAffine(img_rgb, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    x, y, bw, bh = face["box"]
    # rotate the box centre too
    bx, by = M @ np.array([x + bw / 2, y + bh / 2, 1.0])
    side = int(max(bw, bh) * (1 + 2 * margin))
    x0, y0 = int(bx - side / 2), int(by - side / 2)
    x1, y1 = x0 + side, y0 + side
    pad = [max(0, -x0), max(0, -y0), max(0, x1 - w), max(0, y1 - h)]
    if any(pad):
        rotated = cv2.copyMakeBorder(rotated, pad[1], pad[3], pad[0], pad[2], cv2.BORDER_REFLECT)
        x0 += pad[0]; x1 += pad[0]; y0 += pad[1]; y1 += pad[1]
    crop = rotated[y0:y1, x0:x1]
    return cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
