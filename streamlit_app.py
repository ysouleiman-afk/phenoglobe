"""
PhenoGlobe on Streamlit (for Streamlit Community Cloud).

Uploads happen in Streamlit; the analysis runs in pipeline.py; the result panel, 3D globe
and music player are the same static/index.html, embedded in "embed mode" with the result
injected. Static assets are served by Streamlit from ./static at /app/static
(enableStaticServing in .streamlit/config.toml).
"""
import json
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import pipeline

BASE = Path(__file__).parent
STATIC = BASE / "static"

st.set_page_config(page_title="PhenoGlobe", page_icon="🌍", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; padding-bottom: 0; max-width: 1400px; }
  h1 { margin-bottom: 0; }
  [data-testid="stFileUploader"] section { padding: 0.4rem; }
  iframe { border-radius: 16px; }
</style>
""", unsafe_allow_html=True)

st.title("Pheno🌍Globe")
st.caption("Upload two shots of your face. The globe heats up where that look is common, "
           "and the speakers play something from there. Toy, not a DNA test.")

col1, col2 = st.columns(2)
with col1:
    f1 = st.file_uploader("Photo 1 · front-facing", type=["jpg", "jpeg", "png", "webp"], key="p1")
with col2:
    f2 = st.file_uploader("Photo 2 · a second angle", type=["jpg", "jpeg", "png", "webp"], key="p2")
with st.expander("…or use the camera"):
    cam = st.camera_input("Take a shot")
if cam is not None and f1 is None:
    f1 = cam
elif cam is not None and f2 is None:
    f2 = cam

go = st.button("Analyze my face", type="primary", disabled=not (f1 and f2), use_container_width=True)

if go:
    with st.spinner("Detecting faces and comparing against 7,000 reference faces…"):
        with tempfile.TemporaryDirectory(prefix="phenoglobe_") as tmp:
            paths, names = [], []
            for i, f in enumerate((f1, f2)):
                p = Path(tmp) / f"shot{i}{Path(f.name).suffix or '.jpg'}"
                p.write_bytes(f.getvalue())
                paths.append(str(p)); names.append(f.name)
            try:
                st.session_state["result"] = pipeline.analyze_paths(paths, names)
            except pipeline.AnalysisError as exc:
                st.session_state.pop("result", None)
                st.error(str(exc))

result = st.session_state.get("result")
if result:
    s = result["summary"]
    st.subheader(s["label"])
    bits = [f"{s['confidence']} confidence"]
    if result.get("age"): bits.append(f"looks ~{result['age']}")
    if result.get("gender"): bits.append(result["gender"].lower())
    bits.append(s["method"])
    st.caption(" · ".join(bits))
    for w in result.get("warnings", []):
        st.warning(w)
    if s["confidence"] == "low":
        st.info("A flat spread means the models couldn't pin it down. Two bright, front-facing shots help a lot.")

    html = (STATIC / "index.html").read_text(encoding="utf-8")
    inject = (f"<script>window.PHENO_DATA = {json.dumps(result)}; window.PHENO_BASE = '/app/static';</script>")
    html = html.replace("<title>PhenoGlobe</title>", "<title>PhenoGlobe</title>" + inject, 1)
    components.html(html, height=760, scrolling=False)
    st.caption("Music: Kevin MacLeod (incompetech.com), CC BY 3.0 · Map: Natural Earth · "
               "Models: FairFace, InsightFace ArcFace, OpenCV YuNet · References: Wikidata")
