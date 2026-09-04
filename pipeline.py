"""
The PhenoGlobe analysis pipeline, independent of any web framework.

    analyze_paths(["a.jpg", "b.jpg"]) -> result dict (see bottom of analyze_paths)

Used by main.py (FastAPI) and streamlit_app.py (Streamlit Cloud).
"""
import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2
import numpy as np

import detect
import embed
import fairface
import knn
import populations as P
import refine
from phenotypes import LABELS, MUSIC_FOR_TOP_COUNTRY

USE_DEEPFACE = os.environ.get("PHENO_DEEPFACE", "auto")  # auto | 1 | 0
FF_WEIGHT = float(os.environ.get("PHENO_FAIRFACE_WEIGHT", "0.65"))
REFINER_WEIGHT = float(os.environ.get("PHENO_REFINER_WEIGHT", "0.5"))
KNN_WEIGHT = float(os.environ.get("PHENO_KNN_WEIGHT", "0.6"))


class AnalysisError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- optional DeepFace
def deepface_ready() -> bool:
    if USE_DEEPFACE == "0":
        return False
    weights = Path.home() / ".deepface" / "weights" / "race_model_single_batch.h5"
    if USE_DEEPFACE == "auto" and not weights.exists():
        return False
    try:
        import deepface  # noqa: F401
        return True
    except ImportError:
        return False


_df = None


def deepface_race(crop_rgb):
    global _df
    if _df is None:
        from deepface import DeepFace
        _df = DeepFace
    res = _df.analyze(img_path=crop_rgb[:, :, ::-1], actions=["race"], enforce_detection=False,
                      detector_backend="skip", silent=True)
    return {k: float(v) / 100 for k, v in res[0]["race"].items()}


def expand_deepface(df6: dict, ff7: dict | None) -> dict:
    out = {c: 0.0 for c in P.MACROS}
    for k, v in df6.items():
        if k == "asian":
            ea, sea = (ff7 or {}).get("asian", 0.6), (ff7 or {}).get("southeast asian", 0.4)
            r = ea / (ea + sea) if (ea + sea) > 0 else 0.6
            out["asian"] += v * r
            out["southeast asian"] += v * (1 - r)
        else:
            out[k] += v
    return out


# ---------------------------------------------------------------- corrections & checks
def mediterranean_correction(m: dict[str, float]) -> dict[str, float]:
    """FairFace files many Southern-European / Levantine faces under Latino_Hispanic. 'Latino' is an
    admixture label, not a phenotype, so when a European signal is also present move part of it back."""
    m = dict(m)
    w, l = m.get("white", 0.0), m.get("latino hispanic", 0.0)
    if l > 0.05 and w > 0.10:
        f = min(0.6, w / (w + l))
        m["white"] = w + l * f
        m["latino hispanic"] = l * (1 - f)
    return m


def eurasian_correction(m: dict[str, float]) -> dict[str, float]:
    """The same 'Latino' bucket also swallows Central Asian / Turkic / Siberian faces (East-Asian features
    plus a European signal). Hand part of the Latino mass back to the East-Asian macro in that case."""
    m = dict(m)
    a, l, w = m.get("asian", 0.0), m.get("latino hispanic", 0.0), m.get("white", 0.0)
    if l > 0.10 and a > 0.10 and w > 0.10:
        g = min(0.6, a / (a + l))
        m["asian"] = a + l * g
        m["latino hispanic"] = l * (1 - g)
        a, w = m["asian"], m["white"]
        h = min(0.4, a / (a + w))
        m["asian"] = a + w * h
        m["white"] = w * (1 - h)
    return m


def quality_warnings(face: dict, crop: np.ndarray) -> list[str]:
    warns = []
    x, y, w, h = face["box"]
    if min(w, h) < 80:
        warns.append("face is small in the photo; use a closer shot")
    if cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)[:, :, 1].mean() < 18:
        warns.append("photo looks black-and-white; skin tone can't be read")
    (lx, ly), (rx, ry) = face["eyes"]
    if abs(rx - lx) < 0.28 * w:
        warns.append("face is turned to the side; use a front-facing shot")
    if face["score"] < 0.75:
        warns.append("low face-detection confidence")
    return warns


def jpeg_bytes(rgb: np.ndarray, quality: int = 90) -> bytes:
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()


def status() -> dict:
    return {"fairface": fairface.available(), "deepface": deepface_ready(), "refiner": refine.provider(),
            "knn": knn.available(), "knn_refs": knn.counts()}


# ---------------------------------------------------------------- per-photo
def analyze_one(path: str, use_df: bool) -> dict | None:
    img = detect.load_rgb(path)
    faces = detect.detect(img)
    if not faces:
        return None
    face = faces[0]
    crop = detect.align_crop(img, face)
    big = detect.align_crop(img, face, margin=0.45, size=512)
    shot = {"face_confidence": face["score"], "region": dict(zip("xywh", face["box"])), "models": [],
            "warnings": quality_warnings(face, crop), "big_jpeg": jpeg_bytes(big)}
    probs = None
    if fairface.available():
        ff = fairface.predict(crop)
        probs = {c: ff["buckets"].get(c, 0.0) for c in P.MACROS}
        shot.update(age=ff["age"], gender=ff["gender"], fairface=ff["race"])
        shot["models"].append("FairFace")
    if use_df:
        df = expand_deepface(deepface_race(crop), probs)
        shot["deepface"] = df
        shot["models"].append("DeepFace")
        probs = {c: FF_WEIGHT * probs[c] + (1 - FF_WEIGHT) * df[c] for c in P.MACROS} if probs else df
    if probs is None:
        raise AnalysisError(503, "No classifier available: models/fairface.onnx is missing and DeepFace is disabled.")
    shot["macro_raw"] = probs
    shot["macro"] = eurasian_correction(mediterranean_correction(probs))
    if embed.available() and knn.available():
        shot["knn"] = knn.score(embed.embed(img, face))
        shot["models"].append("reference-kNN")
    return shot


# ---------------------------------------------------------------- whole request
def analyze_paths(paths: list[str], names: list[str] | None = None) -> dict:
    names = names or [Path(p).name for p in paths]
    use_df = deepface_ready()
    shots = []
    for path, name in zip(paths, names):
        try:
            shot = analyze_one(path, use_df)
        except AnalysisError:
            raise
        except Exception as exc:
            raise AnalysisError(400, f"Could not analyze {name}: {exc}")
        if shot:
            shots.append(shot)
    if not shots:
        raise AnalysisError(422, "No face found in either photo. Try a clearer, front-facing shot.")

    weights = [max(s["face_confidence"], 0.05) for s in shots]
    total = sum(weights)
    macro = {c: sum(s["macro"][c] * w for s, w in zip(shots, weights)) / total for c in P.MACROS}
    norm = sum(macro.values()) or 1.0
    macro = {k: v / norm for k, v in macro.items()}

    best = max(shots, key=lambda s: s["face_confidence"])
    knn_pops = None
    if all("knn" in s for s in shots):
        keys = shots[0]["knn"].keys()
        knn_pops = {p: sum(s["knn"][p] * w for s, w in zip(shots, weights)) / total for p in keys}

    refiner, shares = refine.refine(best["big_jpeg"], macro)
    pops = None
    if shares:
        ref_macro = {m: sum(shares[p] for p in P.BY_MACRO[m]) for m in P.MACROS}
        macro = {m: (1 - REFINER_WEIGHT) * macro[m] + REFINER_WEIGHT * ref_macro[m] for m in P.MACROS}
        heur = P.heuristic_split(macro)
        split = {}
        for m in P.MACROS:
            tot = sum(shares[p] for p in P.BY_MACRO[m])
            split[m] = {p: shares[p] / tot for p in P.BY_MACRO[m]} if tot > 0.02 else heur[m]
        method = f"FairFace + {refiner}"
    elif knn_pops:
        heur = P.combine(macro, P.heuristic_split(macro))
        pops = {p: KNN_WEIGHT * knn_pops.get(p, 0.0) + (1 - KNN_WEIGHT) * heur[p] for p in P.POPULATIONS}
        tot = sum(pops.values()) or 1.0
        pops = {p: v / tot for p, v in pops.items()}
        macro = {m: sum(pops[p] for p in P.BY_MACRO[m]) for m in P.MACROS}
        method = f"FairFace + reference-kNN ({len(knn_pops)} populations)"
    else:
        split = P.heuristic_split(macro)
        method = "FairFace + heuristic split" + (f" ({refiner})" if refiner else "")

    if pops is None:
        pops = P.combine(macro, split)
    heat = P.heatmap(pops)
    label, primary, confidence = P.label(pops)
    top_iso = max(heat, key=heat.get) if heat else None
    home = P.POPULATIONS[primary]["countries"]
    music_iso = max(home, key=lambda iso: home[iso] * (0.5 + heat.get(iso, 0.0))) if home else top_iso
    music = MUSIC_FOR_TOP_COUNTRY.get(music_iso, P.POPULATIONS[primary]["music"])

    ages = [s["age"] for s in shots if "age" in s]
    genders = [s["gender"] for s in shots if "gender" in s]
    warnings = sorted({w for s in shots for w in s["warnings"]})
    return {
        "populations": P.as_list(pops, 10),
        "macro": {k: round(v, 4) for k, v in macro.items()},
        "macro_labels": LABELS,
        "summary": {"label": label, "primary": primary, "confidence": confidence, "music": music,
                    "music_iso": music_iso, "method": method},
        "heat": heat,
        "age": round(sum(ages) / len(ages)) if ages else None,
        "gender": max(set(genders), key=genders.count) if genders else None,
        "faces_used": len(shots),
        "models": best["models"],
        "warnings": warnings,
        "shots": [{"face_confidence": round(s["face_confidence"], 3), "region": s["region"],
                   "fairface": s.get("fairface"), "warnings": s["warnings"]} for s in shots],
    }
