"""
Build the population reference set: labelled face embeddings from Wikidata.

For every population in populations.py we pull public figures whose ethnic group (P172)
or citizenship+birthplace (P27 + P19) matches, fetch their Wikidata photo (P18) as a
480px thumbnail, detect + align the largest face, and store its ArcFace embedding.
Only the 512-d vectors and labels are kept (models/reference.npz); no photos are stored.

  python build_reference.py            # resumable; skips populations already at target
  python build_reference.py caucasus   # just one population
"""
import io, json, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(__file__).parent
OUT = BASE / "models" / "reference.npz"
PROGRESS = BASE / "models" / "reference_progress.json"
UA = {"User-Agent": "PhenoGlobe/1.0 (personal project; yusufsouleimanov@gmail.com)"}
TARGET = 220          # faces per population
PER_SOURCE = 140      # cap per country / group so one source doesn't dominate
MIN_FACE = 56

# population -> list of sources. ("country", QID) uses citizenship + born there; ("group", name) uses P172.
SOURCES = {
    "nw_european": [("country", "Q145", "United Kingdom"), ("country", "Q27", "Ireland"), ("country", "Q55", "Netherlands"), ("country", "Q31", "Belgium"), ("country", "Q142", "France")],
    "nordic": [("country", "Q34", "Sweden"), ("country", "Q20", "Norway"), ("country", "Q33", "Finland"), ("country", "Q35", "Denmark"), ("country", "Q189", "Iceland")],
    "central_european": [("country", "Q183", "Germany"), ("country", "Q40", "Austria"), ("country", "Q213", "Czech Republic"), ("country", "Q28", "Hungary"), ("country", "Q39", "Switzerland")],
    "east_european": [("country", "Q159", "Russia"), ("country", "Q212", "Ukraine"), ("country", "Q36", "Poland"), ("country", "Q184", "Belarus"), ("country", "Q37", "Lithuania")],
    "south_european": [("country", "Q38", "Italy"), ("country", "Q29", "Spain"), ("country", "Q45", "Portugal"), ("country", "Q233", "Malta")],
    "balkan": [("country", "Q41", "Greece"), ("country", "Q403", "Serbia"), ("country", "Q222", "Albania"), ("country", "Q219", "Bulgaria"), ("country", "Q224", "Croatia"), ("country", "Q221", "North Macedonia"), ("country", "Q225", "Bosnia and Herzegovina")],
    "anatolian": [("country", "Q43", "Turkey"), ("group", "Turkish people")],
    "caucasus": [("country", "Q227", "Azerbaijan"), ("country", "Q399", "Armenia"), ("country", "Q230", "Georgia"), ("group", "Azerbaijanis"), ("group", "Armenians"), ("group", "Georgians"), ("group", "Chechens")],
    "levantine": [("country", "Q822", "Lebanon"), ("country", "Q858", "Syria"), ("country", "Q810", "Jordan"), ("country", "Q219060", "State of Palestine"), ("group", "Palestinians")],
    "mesopotamian": [("country", "Q796", "Iraq"), ("country", "Q817", "Kuwait"), ("country", "Q398", "Bahrain"), ("group", "Assyrian people")],
    "arabian": [("country", "Q851", "Saudi Arabia"), ("country", "Q805", "Yemen"), ("country", "Q842", "Oman"), ("country", "Q878", "United Arab Emirates"), ("country", "Q846", "Qatar")],
    "iranian": [("country", "Q794", "Iran"), ("country", "Q889", "Afghanistan"), ("country", "Q863", "Tajikistan"), ("group", "Persians"), ("group", "Kurds")],
    "maghrebi": [("country", "Q1028", "Morocco"), ("country", "Q262", "Algeria"), ("country", "Q948", "Tunisia"), ("country", "Q1016", "Libya"), ("group", "Berbers")],
    "egyptian": [("country", "Q79", "Egypt"), ("country", "Q1049", "Sudan")],
    "north_indian": [("group", "Punjabis"), ("group", "Gujarati people"), ("group", "Marathi people"), ("group", "Rajput"), ("group", "Kashmiris"), ("country", "Q837", "Nepal")],
    "south_indian": [("group", "Tamils"), ("group", "Telugu people"), ("group", "Malayali"), ("group", "Kannada people"), ("group", "Sinhalese people"), ("country", "Q854", "Sri Lanka")],
    "pashtun_pakistani": [("group", "Pashtuns"), ("country", "Q843", "Pakistan")],
    "bengali": [("group", "Bengalis"), ("country", "Q902", "Bangladesh")],
    "east_asian": [("country", "Q148", "China"), ("country", "Q17", "Japan"), ("country", "Q884", "South Korea"), ("country", "Q865", "Taiwan")],
    "central_asian": [("country", "Q232", "Kazakhstan"), ("country", "Q711", "Mongolia"), ("country", "Q813", "Kyrgyzstan"), ("country", "Q265", "Uzbekistan"), ("group", "Kazakhs"), ("group", "Uyghurs"), ("group", "Mongols")],
    "himalayan": [("country", "Q917", "Bhutan"), ("group", "Tibetan people"), ("group", "Sherpa people"), ("group", "Newar people"), ("group", "Gurung people")],
    "siberian": [("group", "Yakuts"), ("group", "Buryats"), ("group", "Inuit"), ("group", "Tuvans"), ("group", "Evenks"), ("group", "Chukchi people")],
    "mainland_sea": [("country", "Q881", "Vietnam"), ("country", "Q869", "Thailand"), ("country", "Q424", "Cambodia"), ("country", "Q819", "Laos"), ("country", "Q836", "Myanmar")],
    "austronesian": [("country", "Q252", "Indonesia"), ("country", "Q928", "Philippines"), ("country", "Q833", "Malaysia"), ("group", "Javanese people"), ("group", "Filipinos")],
    "melanesian": [("country", "Q691", "Papua New Guinea"), ("country", "Q712", "Fiji"), ("country", "Q685", "Solomon Islands"), ("country", "Q686", "Vanuatu"), ("group", "Papuans")],
    "west_african": [("country", "Q1033", "Nigeria"), ("country", "Q117", "Ghana"), ("country", "Q1041", "Senegal"), ("country", "Q1008", "Ivory Coast"), ("group", "Yoruba people"), ("group", "Igbo people"), ("group", "Akan people")],
    "central_african": [("country", "Q974", "Democratic Republic of the Congo"), ("country", "Q1009", "Cameroon"), ("country", "Q971", "Republic of the Congo"), ("country", "Q1000", "Gabon"), ("country", "Q916", "Angola")],
    "east_african": [("country", "Q114", "Kenya"), ("country", "Q1036", "Uganda"), ("country", "Q924", "Tanzania"), ("country", "Q1037", "Rwanda")],
    "horn_african": [("country", "Q115", "Ethiopia"), ("country", "Q1045", "Somalia"), ("country", "Q986", "Eritrea"), ("country", "Q977", "Djibouti"), ("group", "Somalis"), ("group", "Amhara people"), ("group", "Oromo people")],
    "sahelian": [("country", "Q912", "Mali"), ("country", "Q1032", "Niger"), ("country", "Q1025", "Mauritania"), ("country", "Q657", "Chad"), ("group", "Fula people"), ("group", "Tuareg people")],
    "southern_african": [("group", "Zulu people"), ("group", "Xhosa people"), ("group", "Shona people"), ("country", "Q954", "Zimbabwe"), ("country", "Q963", "Botswana"), ("country", "Q1030", "Namibia"), ("country", "Q1013", "Lesotho")],
    "african_diaspora": [("group", "African Americans"), ("group", "Afro-Brazilians"), ("country", "Q790", "Haiti"), ("country", "Q766", "Jamaica")],
    "mesoamerican": [("country", "Q96", "Mexico"), ("country", "Q774", "Guatemala"), ("country", "Q783", "Honduras"), ("country", "Q792", "El Salvador"), ("country", "Q811", "Nicaragua")],
    "andean": [("country", "Q419", "Peru"), ("country", "Q750", "Bolivia"), ("country", "Q736", "Ecuador"), ("group", "Quechua people"), ("group", "Aymara people")],
    "caribbean_hispanic": [("country", "Q241", "Cuba"), ("country", "Q786", "Dominican Republic"), ("country", "Q1183", "Puerto Rico"), ("country", "Q717", "Venezuela"), ("country", "Q739", "Colombia")],
    "southern_cone": [("country", "Q414", "Argentina"), ("country", "Q77", "Uruguay"), ("country", "Q298", "Chile"), ("country", "Q155", "Brazil")],
}


# ---------------------------------------------------------------- wikidata
def wd_api(params):
    params["format"] = "json"
    req = urllib.request.Request("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params), headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))


def sparql(query, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request("https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query, "format": "json"}),
                                         headers={**UA, "Accept": "application/sparql-results+json"})
            return json.load(urllib.request.urlopen(req, timeout=180))["results"]["bindings"]
        except Exception as e:
            print(f"   sparql retry {i + 1}: {e}", flush=True)
            time.sleep(5 * (i + 1))
    return []


def label_of(qid):
    d = wd_api({"action": "wbgetentities", "ids": qid, "props": "labels", "languages": "en"})
    return d["entities"][qid].get("labels", {}).get("en", {}).get("value", "?")


def resolve_group(name):
    d = wd_api({"action": "wbsearchentities", "search": name, "language": "en", "type": "item", "limit": 6})
    for it in d["search"]:
        desc = it.get("description", "").lower()
        if any(k in desc for k in ("ethnic", "people", "nation", "inhabitants", "group")):
            return it["id"], it["label"]
    return (d["search"][0]["id"], d["search"][0]["label"]) if d["search"] else (None, name)


def people(source):
    kind, qid, name = source if len(source) == 3 else (source[0], None, source[1])
    if kind == "group":
        qid, lab = resolve_group(name)
        if not qid:
            return name, []
        q = f"""SELECT ?p ?img WHERE {{ ?p wdt:P31 wd:Q5; wdt:P172 wd:{qid}; wdt:P18 ?img. }} LIMIT {PER_SOURCE * 2}"""
    else:
        lab = label_of(qid)
        if lab.lower() != name.lower():
            print(f"   QID label mismatch: {qid} = {lab!r}, expected {name!r}; resolving by name", flush=True)
            qid, lab = resolve_group(name)
        q = f"""SELECT ?p ?img WHERE {{ ?p wdt:P31 wd:Q5; wdt:P27 wd:{qid}; wdt:P18 ?img; wdt:P19 ?pob. ?pob wdt:P17 wd:{qid}.
                ?p wdt:P569 ?dob. FILTER(YEAR(?dob) >= 1920) }} LIMIT {PER_SOURCE * 2}"""
    rows = sparql(q)
    return lab, [(r["p"]["value"].rsplit("/", 1)[1], r["img"]["value"]) for r in rows]


# ---------------------------------------------------------------- images
def fetch_thumb(img_url):
    """Wikidata P18 URLs are Special:FilePath links; ask for a 480px thumbnail."""
    url = img_url + ("&" if "?" in img_url else "?") + "width=480"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def face_embedding(jpeg_bytes):
    import detect, embed
    arr = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        return None
    img = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    faces = detect.detect(img)
    if not faces:
        return None
    f = faces[0]
    x, y, w, h = f["box"]
    if f["score"] < 0.8 or min(w, h) < MIN_FACE:
        return None
    (lx, ly), (rx, ry) = f["eyes"]
    if abs(rx - lx) < 0.28 * w:  # profile view
        return None
    crop = img[y:y + h, x:x + w]
    if crop.size and cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)[:, :, 1].mean() < 18:  # greyscale / statue
        return None
    return embed.embed(img, f)


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    X, y, ids = [], [], []
    if OUT.exists():
        d = np.load(OUT, allow_pickle=True)
        X, y, ids = list(d["X"]), list(d["y"]), list(d["ids"])
    have = {}
    for lab in y:
        have[lab] = have.get(lab, 0) + 1
    seen = set(ids)
    pops = only or list(SOURCES)
    for pop in pops:
        if have.get(pop, 0) >= TARGET:
            print(f"{pop}: already {have[pop]}", flush=True)
            continue
        print(f"\n== {pop} (have {have.get(pop, 0)})", flush=True)
        for src in SOURCES[pop]:
            if have.get(pop, 0) >= TARGET:
                break
            lab, rows = people(src)
            rows = [(pid, url) for pid, url in rows if pid not in seen][:PER_SOURCE]
            print(f"   {lab}: {len(rows)} candidates", flush=True)
            got = 0
            with ThreadPoolExecutor(max_workers=6) as ex:
                blobs = list(ex.map(lambda r: _safe_fetch(r[1]), rows))
            for (pid, url), blob in zip(rows, blobs):
                if have.get(pop, 0) >= TARGET:
                    break
                if not blob:
                    continue
                try:
                    e = face_embedding(blob)
                except Exception:
                    e = None
                if e is None:
                    continue
                X.append(e); y.append(pop); ids.append(pid); seen.add(pid)
                have[pop] = have.get(pop, 0) + 1
                got += 1
            print(f"      +{got} faces (total {have.get(pop, 0)})", flush=True)
            np.savez_compressed(OUT, X=np.array(X, dtype=np.float32), y=np.array(y), ids=np.array(ids))
            time.sleep(1)
    PROGRESS.write_text(json.dumps(have, indent=1))
    print("\nDONE", {k: have[k] for k in sorted(have)})


def _safe_fetch(url):
    try:
        return fetch_thumb(url)
    except Exception:
        return None


if __name__ == "__main__":
    main()
