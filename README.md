# PhenoGlobe

Upload two photos of your face. FairFace (a ResNet-34 trained on a balanced
108k-face dataset, run through ONNX Runtime) estimates your phenotype across seven
groups, a 3D globe heats up where that look is common, and a regional track plays.

## Run

    run.bat            # or: .venv\Scripts\python -m uvicorn main:app --port 8000

Open http://localhost:8000. Analysis takes well under a second per photo on CPU.

Models (in `models/`): `yunet.onnx` (OpenCV face detector, 230 KB) and
`fairface.onnx` (85 MB, from huggingface.co/garavv/fairface-onnx). DeepFace is an
optional second opinion: install `deepface tensorflow tf-keras` in the venv and run
with `PHENO_DEEPFACE=1` to download its 500 MB race model and ensemble the two.

## Population breakdown (IllustrativeDNA-style)

FairFace only knows seven broad groups. `populations.py` maps them onto 37 finer
populations (Northwestern European, Balkan & Aegean, Levantine, Caucasus, Central
Asian, Andean, Sahelian, ...) each with its own country weights. The split inside a
broad group comes from:

- a **vision-LLM refiner** (`refine.py`) when a key is set - `ANTHROPIC_API_KEY`
  (Claude, `claude-opus-5`) or `GEMINI_API_KEY` (Gemini 2.5 Flash). It looks at
  the aligned face crop, gets FairFace's numbers as a prior, and scores every
  population with structured JSON. This is what makes the result feel like a
  real report; without it the app can only reshape FairFace's seven numbers.
- otherwise a **heuristic** that uses the *shape* of the FairFace distribution
  (e.g. European + Middle-Eastern signal -> Southern European / Anatolian / Levantine;
  East-Asian + European signal -> Central Asian). Two corrections run first because
  FairFace's "Latino" bucket swallows Mediterranean and Central-Asian faces.

- a **reference-face nearest-neighbour model** (`knn.py`) built by `build_reference.py`:
  for every population it pulls ~220 public figures from Wikidata whose ethnic group
  (P172) or citizenship + birthplace (P27/P19) matches, embeds their photos with
  ArcFace (`embed.py`, InsightFace `w600k_mbf.onnx`) and keeps only the 512-d vectors
  in `models/reference.npz`. At run time your face is compared against all of them and
  each population is scored by its top-k similarity. This is the "model trained on the
  Middle East / West Asia" - and every other region - and it runs fully offline.
  Rebuild or extend it with `.venv\Scripts\python build_reference.py [population]`;
  `python knn.py` prints per-population counts and a leave-one-out accuracy check.
  Current set: 35 populations x ~220 faces (7,300 embeddings). Leave-one-out on the
  citizenship-labelled references: 35% top-1 and 57% top-3 over 35 fine populations
  (chance 3%), 66% on the seven broad groups. Caucasus vs. any European group is the
  strongest separation (66% top-1 among 8 European/West-Asian classes); neighbouring
  European groups overlap heavily and come out as a spread, not one name.

Priority when several are available: vision-LLM refiner > reference-kNN (blended with
the heuristic, weight `PHENO_KNN_WEIGHT`, default 0.6) > heuristic.

The result panel also shows input-quality warnings (black-and-white photo, profile
view, small face) since those are the main cause of silly answers.

## How it works

- `main.py` – FastAPI. `POST /analyze` detects + eye-aligns the largest face in
  each shot (`detect.py`, YuNet), classifies it (`fairface.py`), weights shots by
  detector confidence, and returns probabilities, a phenotype label, a music
  profile, and a per-country heat score.
- `phenotypes.py` – six phenotype buckets x hand-made country weights. The heat
  map is the probability-weighted blend, so mixed results light up mixed regions.
  Blend labels (e.g. "Mediterranean / Levantine") kick in when two buckets are
  both strong.
- `static/index.html` – globe.gl (Three.js) globe with extruded heat polygons,
  pulsing rings on the top countries, fly-to camera, tiers (hot / warm / possible).
- `static/tracks.json` + `static/tracks/` – one real track per country / profile
  (Kevin MacLeod, CC BY 3.0, fetched from Wikimedia Commons by `fetch_macleod.py`,
  trimmed to ~90 s at 96 kbps by `transcode_tracks.py`). The player picks the
  hottest country that has a track, else the profile track.
- `static/music.js` – Web Audio synth fallback used only when no track exists.

Toy, not science. Phenotype != ancestry != nationality.
