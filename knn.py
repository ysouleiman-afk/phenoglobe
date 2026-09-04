"""
Nearest-neighbour population scoring over the Wikidata reference embeddings.

score(embedding) -> {population: probability}. For each population we take the mean of the
top-k cosine similarities to its reference faces and turn the vector of per-population
scores into probabilities with a softmax (temperature T). Populations with too few
references are ignored.
"""
import os
from pathlib import Path

import numpy as np

REF = Path(__file__).parent / "models" / "reference.npz"
K = int(os.environ.get("PHENO_KNN_K", "12"))
T = float(os.environ.get("PHENO_KNN_T", "0.015"))
MIN_REFS = 25
MIN_POPS = 12        # don't score until the reference set covers a reasonable spread ...
MIN_MACROS = 5       # ... of populations and macro groups (otherwise everything maps to the few present)
_cache = None
_mtime = None


def load():
    """Reload automatically when build_reference.py has appended to the file."""
    global _cache, _mtime
    if not REF.exists():
        return None
    mtime = REF.stat().st_mtime
    if _cache is None or mtime != _mtime:
        try:
            d = np.load(REF, allow_pickle=True)
            X, y = d["X"].astype(np.float32), d["y"].astype(str)
            idx = {p: np.where(y == p)[0] for p in sorted(set(y))}
            idx = {p: i for p, i in idx.items() if len(i) >= MIN_REFS}
            _cache = {"X": X, "y": y, "idx": idx, "baseline": _baseline(X, y, idx)}
            _mtime = mtime
        except Exception:
            pass  # file mid-write; keep whatever we had
    return _cache


def _topk_mean(sims_block: np.ndarray, k: int) -> np.ndarray:
    """sims_block: (n_queries, n_refs) -> mean of the top-k per row."""
    k = min(k, sims_block.shape[1])
    part = np.partition(sims_block, -k, axis=1)[:, -k:]
    return part.mean(axis=1)


def _baseline(X, y, idx) -> dict[str, float]:
    """Hubness correction: how similar each population's references are to faces that are NOT
    from that population. Populations with generic/low-quality photos score high for everyone;
    subtracting this baseline turns raw similarity into evidence."""
    rng = np.random.default_rng(0)
    probe = rng.choice(len(X), size=min(1500, len(X)), replace=False)
    base = {}
    for p, i in idx.items():
        others = probe[y[probe] != p]
        sims = X[others] @ X[i].T
        base[p] = float(_topk_mean(sims, K).mean())
    return base


def available() -> bool:
    import populations as P
    c = load()
    if not c or len(c["idx"]) < MIN_POPS:
        return False
    return len({P.POPULATIONS[p]["macro"] for p in c["idx"]}) >= MIN_MACROS


def counts() -> dict:
    c = load()
    return {p: int(len(i)) for p, i in c["idx"].items()} if c else {}


def score(emb: np.ndarray, exclude_id: int | None = None) -> dict[str, float]:
    c = load()
    sims = c["X"] @ emb
    if exclude_id is not None:
        sims[exclude_id] = -1.0
    per_pop = {}
    for p, i in c["idx"].items():
        s = np.sort(sims[i])[::-1]
        k = min(K, len(s))
        per_pop[p] = float(s[:k].mean()) - c["baseline"].get(p, 0.0)
    vals = np.array(list(per_pop.values()))
    z = np.exp((vals - vals.max()) / T)
    z /= z.sum()
    return dict(zip(per_pop.keys(), z.tolist()))


def evaluate(n: int = 600, seed: int = 0) -> dict:
    """Leave-one-out sanity check on a random subset: top-1 population and macro accuracy."""
    import populations as P
    c = load()
    rng = np.random.default_rng(seed)
    pool = np.concatenate(list(c["idx"].values()))
    pick = rng.choice(pool, size=min(n, len(pool)), replace=False)
    hit_pop = hit_macro = 0
    for i in pick:
        pr = score(c["X"][i], exclude_id=int(i))
        best = max(pr, key=pr.get)
        truth = c["y"][i]
        hit_pop += best == truth
        hit_macro += P.POPULATIONS[best]["macro"] == P.POPULATIONS[truth]["macro"]
    return {"n": int(len(pick)), "population_top1": hit_pop / len(pick), "macro_top1": hit_macro / len(pick)}


if __name__ == "__main__":
    print(counts())
    print(evaluate())
