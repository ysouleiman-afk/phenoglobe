"""
Download the hand-picked Kevin MacLeod (incompetech, CC BY 3.0) tracks from Wikimedia
Commons into static/tracks and write static/tracks.json.

  python fetch_macleod.py          # download everything not yet present
  python fetch_macleod.py --dry    # just resolve URLs and print sizes
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(__file__).parent
TRACKS = BASE / "static" / "tracks"
UA = {"User-Agent": "PhenoGlobe/1.0 (personal project; yusufsouleimanov@gmail.com)"}
API = "https://commons.wikimedia.org/w/api.php?"

# key -> Commons file title (without "File:"). Lower-case keys are music profiles, upper-case are ISO3.
PICKS = {
    # profiles
    "east_asian": "Ishikari Lore (ISRC USUAN1100192).mp3",
    "southeast_asian": "Cambodian Odyssey (ISRC USUAN1100585).mp3",
    "south_asian": "Jalandhar (ISRC USUAN1400018).mp3",
    "west_african": "Kumasi Groove (ISRC USUAN1100183).mp3",
    "european": "Master of the Feast (ISRC USUAN1400019).mp3",
    "mena": "Ibn Al-Noor (ISRC USUAN1100706).mp3",
    "latin": "No Frills Cumbia (ISRC USUAN1100275).mp3",
    "andean": "Nu Flute (ISRC USUAN1100680).mp3",
    "mediterranean": "Greko (Sketch) (ISRC USUAN1100389).mp3",
    "sahel": "Savannah (Sketch) (ISRC USUAN1100387).mp3",
    "eurasian": "The Sky of our Ancestors (ISRC USUAN1700056).mp3",
    "caucasus": "Truth in the Stones (ISRC USUAN1700059).mp3",
    # East / Southeast Asia
    "JPN": "Senbazuru (ISRC USUAN1100821).mp3",
    "CHN": "Eastern Thought (ISRC USUAN1100682).mp3",
    "TWN": "Eastern Thought (ISRC USUAN1100682).mp3",
    "KOR": "Mountain Emperor (ISRC USUAN1700012).mp3",
    "VNM": "Opium (ISRC USUAN1100371).mp3",
    "THA": "Cambodian Odyssey (ISRC USUAN1100585).mp3",
    "KHM": "Cambodian Odyssey (ISRC USUAN1100585).mp3",
    "IDN": "Tikopia (ISRC USUAN1100827).mp3",
    "PHL": "Tiki Bar Mixer by Kevin MacLeod.ogg",
    "MNG": "The Sky of our Ancestors (ISRC USUAN1700056).mp3",
    # South Asia
    "IND": "Jalandhar (ISRC USUAN1400018).mp3",
    "PAK": "Indore (ISRC USUAN1600041).mp3",
    "BGD": "Dhaka (ISRC USUAN1400003).mp3",
    "LKA": "Naraina (ISRC USUAN1400053).mp3",
    "NPL": "Himalayan Atmosphere (ISRC USUAN1100204).mp3",
    "BTN": "Himalayan Atmosphere (ISRC USUAN1100204).mp3",
    "AFG": "Mystery Bazaar (ISRC USUAN1700005).mp3",
    # Africa
    "NGA": "Tafi Maradi no voice (ISRC USUAN1100740).mp3",
    "GHA": "Kumasi Groove (ISRC USUAN1100183).mp3",
    "SEN": "Digya (ISRC USUAN1200080).mp3",
    "MLI": "Bumba Crossing (ISRC USUAN1500031).mp3",
    "CIV": "Accralate (ISRC USUAN1100341).mp3",
    "CMR": "Dubakupado (ISRC USUAN1100834).mp3",
    "COD": "Dubakupado (ISRC USUAN1100834).mp3",
    "ETH": "Monkoto (ISRC USUAN1100432).mp3",
    "KEN": "Zanzibar (ISRC USUAN1500006).mp3",
    "TZA": "Zanzibar (ISRC USUAN1500006).mp3",
    "ZAF": "AngloZulu (ISRC USUAN1100411).mp3",
    "ZWE": "Ave Marimba (ISRC USUAN1700024).mp3",
    # Europe
    "GBR": "Skye Cuillin (ISRC USUAN1100346).mp3",
    "IRL": "Galway (ISRC USUAN1700016).mp3",
    "FRA": "Parisian (ISRC USUAN1100120).mp3",
    "DEU": "Meanwhile in Bavaria (ISRC USUAN1500057).mp3",
    "AUT": "Meanwhile in Bavaria (ISRC USUAN1500057).mp3",
    "ITA": "Bushwick Tarantella (ISRC USUAN1300002).mp3",
    "ESP": "Sancho Panza gets a Latte (ISRC USUAN1100088).mp3",
    "PRT": "Suonatore di Liuto (ISRC USUAN1400023).mp3",
    "GRC": "Greko (Sketch) (ISRC USUAN1100389).mp3",
    "POL": "Angevin (ISRC USUAN1200110).mp3",
    "RUS": "Padanaya Blokov (ISRC USUAN1100606).mp3",
    "UKR": "Old Road (ISRC USUAN1100725).mp3",
    "SWE": "Moorland (ISRC USUAN1200106).mp3",
    "NOR": "Moorland (ISRC USUAN1200106).mp3",
    "FIN": "Moorland (ISRC USUAN1200106).mp3",
    "HUN": "Master of the Feast (ISRC USUAN1400019).mp3",
    "ROU": "Teller of the Tales (ISRC USUAN1400020).mp3",
    "SRB": "Balzan Groove (ISRC USUAN1100311).mp3",
    "NLD": "Pippin the Hunchback (ISRC USUAN1400005).mp3",
    # Middle East / North Africa
    "TUR": "Mystery Bazaar (ISRC USUAN1700005).mp3",
    "IRN": "Desert City (ISRC USUAN1100564).mp3",
    "IRQ": "Ibn Al-Noor (ISRC USUAN1100706).mp3",
    "SAU": "Tabuk (ISRC USUAN1100818).mp3",
    "JOR": "Tabuk (ISRC USUAN1100818).mp3",
    "EGY": "Temple of the Manes (ISRC USUAN1100053).mp3",
    "MAR": "East of Tunesia (ISRC USUAN1100246).mp3",
    "DZA": "East of Tunesia (ISRC USUAN1100246).mp3",
    "TUN": "East of Tunesia (ISRC USUAN1100246).mp3",
    "LBN": "Ibn Al-Noor (ISRC USUAN1100706).mp3",
    "SYR": "Desert City (ISRC USUAN1100564).mp3",
    "ISR": "Lachaim (ISRC USUAN1100412).mp3",
    # Latin America & Caribbean
    "MEX": "Mariachi Snooze (ISRC USUAN1100166).mp3",
    "BRA": "Suvaco do Cristo (ISRC USUAN1100867).mp3",
    "ARG": "Tango de Manzana (ISRC USUAN1100404).mp3",
    "URY": "Tango de Manzana (ISRC USUAN1100404).mp3",
    "COL": "No Frills Cumbia (ISRC USUAN1100275).mp3",
    "PER": "Nu Flute (ISRC USUAN1100680).mp3",
    "BOL": "Nu Flute (ISRC USUAN1100680).mp3",
    "CHL": "Laid Back Guitars (ISRC USUAN1100181).mp3",
    "CUB": "Cuban Sandwich (ISRC USUAN1600005).mp3",
    "VEN": "Wepa (ISRC USUAN1700020).mp3",
    "DOM": "Notanico Merengue (ISRC USUAN1100130).mp3",
    "PRI": "No Frills Salsa (ISRC USUAN1100133).mp3",
    "JAM": "Montego (ISRC USUAN1100808).mp3",
    # Central Asia / Caucasus
    "KAZ": "The Sky of our Ancestors (ISRC USUAN1700056).mp3",
    "UZB": "Send for the Horses (ISRC USUAN1700028).mp3",
    "GEO": "Truth in the Stones (ISRC USUAN1700059).mp3",
    "ARM": "Silver Flame (ISRC USUAN1700058).mp3",
    "AZE": "River Fire (ISRC USUAN1700055).mp3",
}


def api(params):
    params["format"] = "json"
    for wait in (2, 6, 15, 40, 90):
        try:
            time.sleep(0.5)
            req = urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=40))
        except Exception as e:
            print(f"   retry after {wait}s: {e}", flush=True)
            time.sleep(wait)
    return {}


def resolve(titles):
    out = {}
    titles = sorted(set(titles))
    for i in range(0, len(titles), 50):
        d = api({"action": "query", "titles": "|".join("File:" + t for t in titles[i:i + 50]),
                 "prop": "imageinfo", "iiprop": "url|size|mime|dimensions"})
        for p in d.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            if ii:
                out[p["title"][5:]] = ii
    return out


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"\s*\(ISRC[^)]*\)", "", title.rsplit(".", 1)[0]).lower()).strip("-")


def main():
    dry = "--dry" in sys.argv
    profiles_only = "--profiles" in sys.argv
    TRACKS.mkdir(parents=True, exist_ok=True)
    wanted = {k: v for k, v in PICKS.items() if k.islower() or not profiles_only}
    info = resolve(wanted.values())
    # profiles first so the fallback layer lands before the long tail of countries
    order = [PICKS[k] for k in PICKS if k.islower()] + [PICKS[k] for k in PICKS if not k.islower()]
    info = {t: info[t] for t in dict.fromkeys(order) if t in info}
    missing = [t for t in set(wanted.values()) if t not in info]
    for t in missing:
        print("MISSING on Commons:", t)
    tj = BASE / "static" / "tracks.json"
    tracks = json.loads(tj.read_text(encoding="utf-8")) if tj.exists() and not dry else {"byCountry": {}, "byProfile": {}}
    tracks.setdefault("meta", {})
    mark = TRACKS / ".transcoded"
    transcoded = set(mark.read_text().split()) if mark.exists() else set()
    total = 0
    for title, ii in info.items():
        ext = ".mp3" if "mpeg" in ii["mime"] else ".ogg"
        fname = slug(title) + ext
        dest = TRACKS / fname
        total += ii["size"]
        print(f"{ii.get('duration', 0):5.0f}s {ii['size'] // 1024:5d}KB  {fname}")
        already = fname in transcoded or (dest.exists() and dest.stat().st_size == ii["size"])
        if not dry and not already:
            for attempt in range(4):
                try:
                    req = urllib.request.Request(ii["url"], headers=UA)
                    with urllib.request.urlopen(req, timeout=180) as r, dest.open("wb") as fh:
                        fh.write(r.read())
                    break
                except Exception as e:
                    print("   download retry:", e, flush=True); time.sleep(5 * (attempt + 1))
        if not dry and not dest.exists():
            continue
        if fname in tracks["meta"]:
            continue
        tracks["meta"][fname] = {
            "title": re.sub(r"\s*\(ISRC[^)]*\)", "", title.rsplit(".", 1)[0]),
            "artist": "Kevin MacLeod (incompetech.com)", "license": "CC BY 3.0",
            "source": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(title),
        }
    for key, title in wanted.items():
        if title not in info or (not dry and not (TRACKS / (slug(title) + (".mp3" if "mpeg" in info[title]["mime"] else ".ogg"))).exists()):
            continue
        ii = info[title]
        fname = slug(title) + (".mp3" if "mpeg" in ii["mime"] else ".ogg")
        tracks["byProfile" if key.islower() else "byCountry"][key] = fname
    print(f"{len(info)} unique files, {total / 1e6:.0f} MB total")
    if not dry:
        tj.write_text(json.dumps(tracks, indent=2, ensure_ascii=False), encoding="utf-8")
        print("wrote", tj)


if __name__ == "__main__":
    main()
