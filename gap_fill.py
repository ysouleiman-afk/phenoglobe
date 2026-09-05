"""
Gap-fill the authentic-music catalogue for regions the category crawl missed
(Central Asia, most of Africa, the Levant, Korea/Japan, the Caucasus).

Uses the Commons search API, which is rate-limited and flaky, so it goes slowly
and retries hard. Appends to catalog.json under "search:<term>" keys.
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(__file__).parent
OUT = BASE / "catalog.json"
UA = {"User-Agent": "PhenoGlobe/1.0 (personal project; yusufsouleimanov@gmail.com)"}
API = "https://commons.wikimedia.org/w/api.php?"

TERMS = [
    # public-domain African label reissues on Commons (Opika / Ngoma / Africavox)
    "PDP-CH African music", "PDP-CH Baoule", "PDP-CH Kele", "PDP-CH Zande", "Opika African music",
    "Ngoma African music", "Africavox",
    # Central Asia / Siberia / Caucasus
    "dombra Kazakh", "morin khuur", "Mongolian throat singing", "Kyrgyz komuz", "Uzbek dutar",
    "Chakrulo Georgian", "Georgian polyphonic song", "duduk Armenian", "Tuvan khoomei",
    # East Asia
    "Arirang", "Korean folk song", "gagaku", "shakuhachi honkyoku", "Japanese folk song min'yo",
    # Middle East / North Africa
    "maqam taqsim", "Egyptian folk music", "Moroccan gnawa", "Lebanese dabke", "Persian santur",
    # Africa
    "Ethiopian krar", "Kenyan traditional music", "Zulu traditional song", "mbira dzavadzimu",
    "kora Mandinka", "Senegal sabar", "Malian ngoni", "Congolese traditional music",
    "Somali traditional music", "Sudanese music",
    # Latin America / Caribbean
    "son cubano 1920", "Andean quena", "Bolivian charango", "merengue 1920", "Haitian meringue",
    "mento Jamaica", "Venezuelan joropo",
    # South / Southeast Asia
    "gamelan Java", "kulintang", "Thai traditional music", "Burmese saung", "sitar raga",
]
AUDIO = re.compile(r"\.(ogg|oga|mp3|opus|flac|wav)$", re.I)


def api(params, tries=6):
    params["format"] = "json"
    wait = 3
    for _ in range(tries):
        try:
            time.sleep(1.2)
            req = urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            print(f"   retry {wait}s: {e}", flush=True)
            time.sleep(wait); wait = min(wait * 2, 90)
    return {}


def search(term, limit=30):
    d = api({"action": "query", "list": "search", "srsearch": f"{term} filetype:audio",
             "srnamespace": 6, "srlimit": limit})
    return [r["title"] for r in d.get("query", {}).get("search", []) if AUDIO.search(r["title"])]


def info(titles):
    out = []
    for i in range(0, len(titles), 50):
        d = api({"action": "query", "titles": "|".join(titles[i:i + 50]), "prop": "imageinfo",
                 "iiprop": "url|size|mime|extmetadata"})
        for p in d.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            if not ii or not str(ii.get("mime", "")).startswith("audio/"):
                continue
            em = ii.get("extmetadata", {})
            strip = lambda k: re.sub("<[^>]+>", "", em.get(k, {}).get("value", "")).strip()
            out.append({"title": p["title"], "url": ii["url"], "size": ii["size"], "mime": ii["mime"],
                        "duration": float(ii.get("duration") or 0),
                        "license": em.get("LicenseShortName", {}).get("value", "?"),
                        "artist": strip("Artist")[:80], "desc": strip("ImageDescription")[:200],
                        "iso": None})
    return out


def main():
    catalog = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for term in TERMS:
        key = "search:" + term
        if key in catalog:
            continue
        titles = search(term)
        rows = info(titles) if titles else []
        catalog[key] = rows
        print(f"{len(rows):3d}  {term}", flush=True)
        OUT.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    print("GAPFILL DONE")


if __name__ == "__main__":
    main()
