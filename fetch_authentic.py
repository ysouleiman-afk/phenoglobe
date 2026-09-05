"""
Download the curated set of AUTHENTIC traditional recordings into static/tracks
and write static/tracks.json.

Every entry is a real performance from Wikimedia Commons - field recordings, folk
archives, and historic discs - not generic royalty-free "world-flavoured" library music.
Picks are resolved against catalog.json by substring, so titles can't drift.

  python fetch_authentic.py --dry     # resolve + report, download nothing
  python fetch_authentic.py           # download what's missing
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(__file__).parent
TRACKS = BASE / "static" / "tracks"
CATALOG = BASE / "catalog.json"
UA = {"User-Agent": "PhenoGlobe/1.0 (personal project; yusufsouleimanov@gmail.com)"}

# key -> ordered candidate substrings; the first one found in the catalogue wins.
# Lower-case keys are music profiles (populations), upper-case are ISO-3166 alpha-3.
PICKS = {
    # ---- populations (fallback when the hottest country has no recording of its own)
    "nw_european":      ["Ble Rwyt Ti'n Myned", "Ambell i Gan"],
    "nordic":           ["Gånglåt efter Gulamåraviten", "Byggnan, polska efter Byss Kalle"],
    "central_european": ["01. Augustin; 02. Au claire", "Il contrabbandiere"],
    "east_european":    ["Дyдaрик", "01-Moja-mamuliczko"],
    "south_european":   ["Ciuri, Ciuri", "Il contrabbandiere"],
    "balkan":           ["Rizitiko - Crete 2", "Παϊτούσκα"],
    "anatolian":        ["Kâtibim"],
    "caucasus":         ["Armenian song KHUMAR", "مقام نوا"],
    "levantine":        ["Oud music by Andy R. Jordan 1V2 long.mp3"],
    "mesopotamian":     ["Oud music by Andy R. Jordan 2v2.mp3"],
    "arabian":          ["Oud music by Andy R. Jordan 1V2 short.mp3"],
    "iranian":          ["Santur by Mohammad R Azadehfar"],
    "maghrebi":         ["الفرق بين أهليل و تقرابت"],
    "egyptian":         ["الفرق بين أهليل و تقرابت"],
    "north_indian":     ["Traditional Bhil Wedding Farewell Song"],
    "south_indian":     ["Valaga FuneralDirge"],
    "pashtun_pakistani":["10-Shenidam ke madari megoft", "1-Shabe Mahtab"],
    "bengali":          ["সাঁঝের তারকা আমি"],
    "east_asian":       ["Shanghainese popular song", "大香山"],
    "central_asian":    ["مقام نوا", "Kâtibim"],
    "himalayan":        ["Audio Zill big 3"],
    "siberian":         ["Coucou (chant populaire tchouvache)"],
    "mainland_sea":     ["Hát trống quân"],
    "southeast_asian":  ["Jawa Tengah - Cublak-Cublak Suweng", "Riau - Soleram"],
    "austronesian":     ["Riau - Soleram", "Jawa Tengah - Cublak-Cublak Suweng"],
    "melanesian":       ["Papua - Yamko Rambe Yamko"],
    "west_african":     ["Kpanlogo Rhythmus"],
    "central_african":  ["Blekete rhythm"],
    "east_african":     ["Ngoma Traditional Dance Song- Tanzania"],
    "horn_african":     ["Ngoma Traditional Dance Song- Tanzania"],
    "sahelian":         ["أهليل و اللغة الزناتية", "الفرق بين أهليل و تقرابت"],
    "southern_african": ["Ngoma Traditional Dance Song- Tanzania"],
    "african_diaspora": ["Swing Low, Sweet Chariot - Fisk Jubilee Singers"],
    "mesoamerican":     ["Pajaro carpintero en un fandango en Santiago tuxtla"],
    "andean":           ["Arica - Vals - Montes y Manrique"],
    "caribbean_hispanic":["Nacional joropo - Lionel Belasco"],
    "southern_cone":    ["Carlos Gardel - Congojas"],
    # legacy profile ids still referenced by phenotypes.py
    "european":         ["Ble Rwyt Ti'n Myned"],
    "mena":             ["Oud music by Andy R. Jordan 1V2 long.mp3"],
    "latin":            ["Nacional joropo - Lionel Belasco"],
    "south_asian":      ["Traditional Bhil Wedding Farewell Song"],
    "mediterranean":    ["Ciuri, Ciuri"],
    "sahel":            ["أهليل و اللغة الزناتية"],
    "eurasian":         ["Coucou (chant populaire tchouvache)"],
    # ---- countries with a genuine recording of their own
    "ITA": ["Ciuri, Ciuri"],
    "GRC": ["Rizitiko - Crete 2", "Κόρη Ελένη"],
    "TUR": ["Kâtibim"],
    "ARG": ["Carlos Gardel - Congojas"],
    "URY": ["Carlos Gardel - Pobre amigo"],
    "AZE": ["مقام نوا"],
    "ARM": ["Armenian song KHUMAR"],
    "DZA": ["الفرق بين أهليل و تقرابت"],
    "MAR": ["أهليل و اللغة الزناتية"],
    "POL": ["01-Moja-mamuliczko"],
    "UKR": ["Дyдaрик"],
    "RUS": ["Ты каждый день меня пытаешь"],
    "EST": ["Aleksander Läte - Kuldrannake (Tallinna"],
    "BGR": ["Still White Danube"],
    "SWE": ["Gånglåt efter Gulamåraviten"],
    "FIN": ["En sjömansgosse på stranden stod"],
    "NOR": ["Stämning av langeleik"],
    "DNK": ["Jungfrun hon sitter i buren"],
    "ESP": ["Alborada da Costa da Morte"],
    "GBR": ["Ble Rwyt Ti'n Myned"],
    "CHN": ["Shanghainese popular song"],
    "TWN": ["Thinn-oo-oo"],
    "KOR": ["Doraji Taryeong", "Jindo Arirang"],
    "PRK": ["Jindo Arirang", "Old Arirang"],
    "JPN": ["伊丹のもとかき唄", "伊丹の秋洗い唄"],
    "VNM": ["Hát trống quân"],
    "KHM": ["Phlom Slek"],
    "IDN": ["Jawa Tengah - Cublak-Cublak Suweng"],
    "PNG": ["Papua - Yamko Rambe Yamko"],
    "IND": ["Traditional Bhil Wedding Farewell Song"],
    "LKA": ["Valaga FuneralDirge"],
    "BGD": ["সাঁঝের তারকা আমি"],
    "AFG": ["10-Shenidam ke madari megoft"],
    "PAK": ["1-Shabe Mahtab"],
    "IRN": ["Santur by Mohammad R Azadehfar"],
    "NPL": ["Audio Zill big 3"],
    "NGA": ["Hausa traditional emirate turbening music 03"],
    "GHA": ["Kpanlogo Rhythmus"],
    "TGO": ["Blekete rhythm"],
    "TZA": ["Ngoma Traditional Dance Song- Tanzania"],
    "KEN": ["Ngoma Traditional Dance Song- Tanzania"],
    "USA": ["Swing Low, Sweet Chariot - Fisk Jubilee Singers"],
    "MEX": ["Pajaro carpintero en un fandango en Santiago tuxtla"],
    "PER": ["Arica - Vals - Montes y Manrique"],
    "BOL": ["Huacachina - Tondero - Montes y Manrique"],
    "COL": ["Jorge Áñez Avendaño and Víctor Justiniano Rosales"],
    "VEN": ["Nacional joropo - Lionel Belasco"],
    "TTO": ["Phil Madison - Neighbor Next Door"],
    "JAM": ["Phil Madison - Neighbor Next Door"],
}


def load_catalog():
    d = json.loads(CATALOG.read_text(encoding="utf-8"))
    files = {}
    for rows in d.values():
        for r in rows:
            t = r["title"]
            # when the same recording exists as wav and mp3, keep the smaller one
            if t not in files or r["size"] < files[t]["size"]:
                files[t] = r
    return files


def resolve(files, needles):
    """Best catalogue entry containing one of the needles: compact mp3/ogg, sane length."""
    def rank(r):
        dur = r["duration"]
        s = 0.0
        if r["mime"] in ("audio/mpeg", "audio/ogg"): s += 4          # already compressed
        if r["size"] < 8e6: s += 3
        elif r["size"] < 25e6: s += 1
        else: s -= 2
        if 45 <= dur <= 240: s += 2
        elif dur > 420 or dur < 20: s -= 4
        return s

    for n in needles:
        cands = [r for r in files.values() if n in r["title"]]
        if cands:
            return max(cands, key=rank)
    return None


def slug(title, fallback=None):
    """ASCII-only filename: non-Latin titles (Arabic, Bengali, Japanese, Cyrillic) would
    otherwise produce filenames that are painful to serve and to store in git."""
    import unicodedata
    s = re.sub(r"^File:", "", title)
    s = re.sub(r"\.[a-z0-9]+$", "", s, flags=re.I)
    s = re.sub(r"\s*-\s*(SMV|SVA).*$", "", s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    if len(s) < 3:
        # non-Latin title: derive a stable name from the source so one recording = one file
        import hashlib
        s = "trad-" + hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
    return (s or "track")[:48]


def main():
    dry = "--dry" in sys.argv
    files = load_catalog()
    TRACKS.mkdir(parents=True, exist_ok=True)
    tracks = {"byCountry": {}, "byProfile": {}, "meta": {}}
    chosen, missing, total = {}, [], 0
    for key, needles in PICKS.items():
        r = resolve(files, needles)
        if not r:
            missing.append(key); continue
        m = re.search(r"\.([a-z0-9]{2,5})$", r["title"], re.I)
        ext = ".mp3" if "mpeg" in r["mime"] else ".ogg" if "ogg" in r["mime"] else ("." + m.group(1).lower() if m else ".wav")
        fname = slug(r["title"]) + ext
        chosen[key] = (fname, r)
        tracks["byProfile" if key.islower() else "byCountry"][key] = fname
        if fname not in tracks["meta"]:
            total += r["size"]
            tracks["meta"][fname] = {
                "title": re.sub(r"^File:", "", re.sub(r"\.[a-z0-9]+$", "", r["title"], flags=re.I))[:90],
                "artist": r["artist"] or "traditional", "license": r["license"],
                "source": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(r["title"]),
            }
    print(f"{len(chosen)} keys -> {len(tracks['meta'])} unique recordings, {total/1e6:.0f} MB to fetch")
    if missing:
        print("UNRESOLVED:", ", ".join(missing))
    for key, (fname, r) in sorted(chosen.items()):
        print(f"  {key:20s} {r['duration']:5.0f}s {r['size']//1024:6d}K {r['license'][:11]:12s} {fname}")
    if dry:
        return
    done = set()
    for key, (fname, r) in chosen.items():
        dest = TRACKS / fname
        if fname in done or (dest.exists() and dest.stat().st_size == r["size"]):
            done.add(fname); continue
        for attempt in range(4):
            try:
                req = urllib.request.Request(r["url"], headers=UA)
                with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as fh:
                    fh.write(resp.read())
                print(f"  got {fname} ({dest.stat().st_size//1024}K)", flush=True)
                done.add(fname); break
            except Exception as e:
                print(f"  retry {fname}: {e}", flush=True); time.sleep(5 * (attempt + 1))
    (BASE / "static" / "tracks.json").write_text(json.dumps(tracks, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote static/tracks.json")


if __name__ == "__main__":
    main()
