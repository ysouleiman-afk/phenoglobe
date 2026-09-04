"""
ArcFace face embeddings (InsightFace buffalo_sc / w600k_mbf.onnx, MobileFaceNet, 512-d).

Faces are aligned with the standard 5-point ArcFace template using YuNet's landmarks.
"""
from pathlib import Path

import cv2
import numpy as np

MODEL = Path(__file__).parent / "models" / "w600k_mbf.onnx"
# left eye, right eye, nose tip, left mouth corner, right mouth corner (image coords, 112x112)
TEMPLATE = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
                     [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float32)
_session = None


def available() -> bool:
    if not MODEL.exists():
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


def landmarks5(face: dict) -> np.ndarray:
    """YuNet gives (right eye, left eye, nose, right mouth, left mouth) - sort by x so the
    template order (image-left eye first) holds regardless of naming."""
    (e1, e2), nose, (m1, m2) = face["eyes"], face["nose"], face["mouth"]
    eyes = sorted([e1, e2], key=lambda p: p[0])
    mouth = sorted([m1, m2], key=lambda p: p[0])
    return np.array([eyes[0], eyes[1], nose, mouth[0], mouth[1]], dtype=np.float32)


def align112(img_rgb: np.ndarray, face: dict) -> np.ndarray:
    pts = landmarks5(face)
    M, _ = cv2.estimateAffinePartial2D(pts, TEMPLATE, method=cv2.LMEDS)
    if M is None:
        M = cv2.getAffineTransform(pts[:3], TEMPLATE[:3])
    return cv2.warpAffine(img_rgb, M, (112, 112), borderValue=(0, 0, 0))


def embed(img_rgb: np.ndarray, face: dict) -> np.ndarray:
    """L2-normalised 512-d embedding."""
    chip = align112(img_rgb, face)
    x = (chip.astype(np.float32) - 127.5) / 127.5
    x = x.transpose(2, 0, 1)[None]
    sess = session()
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]
    return out / (np.linalg.norm(out) + 1e-9)
