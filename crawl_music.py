"""
Crawl Wikimedia Commons for AUTHENTIC traditional / folk recordings and write catalog.json.

Unlike generic royalty-free "world-flavoured" library music, everything here is a real
recording: field recordings, folk archives, ethnographic collections and traditional
performances, all under a free licence.

  python crawl_music.py            # resumable; appends to catalog.json
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(__file__).parent
OUT = BASE / "catalog.json"
UA = {"User-Agent": "PhenoGlobe/1.0 (personal project; yusufsouleimanov@gmail.com)"}
API = "https://commons.wikimedia.org/w/api.php?"
AUDIO = re.compile(r"\.(ogg|oga|mp3|opus|flac|wav)$", re.I)

# Country name -> ISO3, used to build per-country category names.
COUNTRIES = {
    "Italy": "ITA", "Spain": "ESP", "Portugal": "PRT", "Greece": "GRC", "France": "FRA",
    "Germany": "DEU", "Austria": "AUT", "Switzerland": "CHE", "Netherlands": "NLD", "Belgium": "BEL",
    "Ireland": "IRL", "Scotland": "GBR", "Wales": "GBR", "England": "GBR", "Denmark": "DNK",
    "Sweden": "SWE", "Norway": "NOR", "Finland": "FIN", "Iceland": "ISL", "Estonia": "EST",
    "Latvia": "LVA", "Lithuania": "LTU", "Poland": "POL", "Czech Republic": "CZE", "Slovakia": "SVK",
    "Hungary": "HUN", "Romania": "ROU", "Bulgaria": "BGR", "Serbia": "SRB", "Croatia": "HRV",
    "Bosnia and Herzegovina": "BIH", "North Macedonia": "MKD", "Albania": "ALB", "Montenegro": "MNE",
    "Slovenia": "SVN", "Ukraine": "UKR", "Belarus": "BLR", "Russia": "RUS", "Moldova": "MDA",
    "Turkey": "TUR", "Cyprus": "CYP", "Georgia (country)": "GEO", "Armenia": "ARM", "Azerbaijan": "AZE",
    "Iran": "IRN", "Iraq": "IRQ", "Syria": "SYR", "Lebanon": "LBN", "Jordan": "JOR", "Israel": "ISR",
    "Palestine": "PSX", "Saudi Arabia": "SAU", "Yemen": "YEM", "Oman": "OMN", "Kuwait": "KWT",
    "Egypt": "EGY", "Sudan": "SDN", "Libya": "LBY", "Tunisia": "TUN", "Algeria": "DZA", "Morocco": "MAR",
    "Mauritania": "MRT", "Mali": "MLI", "Niger": "NER", "Chad": "TCD", "Senegal": "SEN", "Gambia": "GMB",
    "Guinea": "GIN", "Ghana": "GHA", "Nigeria": "NGA", "Benin": "BEN", "Togo": "TGO", "Burkina Faso": "BFA",
    "Ivory Coast": "CIV", "Liberia": "LBR", "Sierra Leone": "SLE", "Cameroon": "CMR", "Gabon": "GAB",
    "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG", "Angola": "AGO",
    "Kenya": "KEN", "Uganda": "UGA", "Tanzania": "TZA", "Rwanda": "RWA", "Burundi": "BDI",
    "Ethiopia": "ETH", "Eritrea": "ERI", "Somalia": "SOM", "Djibouti": "DJI",
    "South Africa": "ZAF", "Zimbabwe": "ZWE", "Zambia": "ZMB", "Botswana": "BWA", "Namibia": "NAM",
    "Mozambique": "MOZ", "Malawi": "MWI", "Madagascar": "MDG", "Lesotho": "LSO",
    "India": "IND", "Pakistan": "PAK", "Bangladesh": "BGD", "Sri Lanka": "LKA", "Nepal": "NPL",
    "Bhutan": "BTN", "Afghanistan": "AFG", "China": "CHN", "Japan": "JPN", "South Korea": "KOR",
    "North Korea": "PRK", "Taiwan": "TWN", "Mongolia": "MNG", "Vietnam": "VNM", "Thailand": "THA",
    "Cambodia": "KHM", "Laos": "LAO", "Myanmar": "MMR", "Malaysia": "MYS", "Indonesia": "IDN",
    "Philippines": "PHL", "Singapore": "SGP", "Brunei": "BRN", "East Timor": "TLS",
    "Kazakhstan": "KAZ", "Uzbekistan": "UZB", "Kyrgyzstan": "KGZ", "Turkmenistan": "TKM",
    "Tajikistan": "TJK", "Papua New Guinea": "PNG", "Fiji": "FJI", "Solomon Islands": "SLB",
    "Vanuatu": "VUT", "New Zealand": "NZL", "Mexico": "MEX", "Guatemala": "GTM", "Honduras": "HND",
    "El Salvador": "SLV", "Nicaragua": "NIC", "Costa Rica": "CRI", "Panama": "PAN", "Cuba": "CUB",
    "Dominican Republic": "DOM", "Puerto Rico": "PRI", "Haiti": "HTI", "Jamaica": "JAM",
    "Trinidad and Tobago": "TTO", "Colombia": "COL", "Venezuela": "VEN", "Ecuador": "ECU",
    "Peru": "PER", "Bolivia": "BOL", "Chile": "CHL", "Argentina": "ARG", "Uruguay": "URY",
    "Paraguay": "PRY", "Brazil": "BRA",
}

# Category name patterns tried for every country above.
PATTERNS = [
    "Category:Audio files of music of {c}",
    "Category:Audio files of folk music of {c}",
    "Category:Folk music of {c}",
    "Category:Traditional music of {c}",
    "Category:Music of {c}",
    "Category:Songs of {c}",
    "Category:Folk songs of {c}",
]

# Instrument / genre categories: authentic performances, tagged by what is played.
EXTRA = [
    "Category:Audio files of oud music", "Category:Oud music", "Category:Koto music",
    "Category:Audio files of bagpipe music", "Category:Bagpipe music", "Category:Duduk",
    "Category:Sitar music", "Category:Audio files of sitar music", "Category:Tabla",
    "Category:Gamelan music", "Category:Audio files of gamelan", "Category:Kora (instrument)",
    "Category:Djembe", "Category:Balalaika music", "Category:Bouzouki music", "Category:Bandura",
    "Category:Charango", "Category:Panpipes", "Category:Erhu", "Category:Guzheng", "Category:Pipa",
    "Category:Shakuhachi", "Category:Shamisen", "Category:Morin khuur", "Category:Dombra",
    "Category:Dutar", "Category:Saz", "Category:Bağlama", "Category:Qanun (instrument)",
    "Category:Santur", "Category:Ney", "Category:Darbuka", "Category:Mbira", "Category:Marimba",
    "Category:Nyckelharpa", "Category:Hardanger fiddle", "Category:Uilleann pipes", "Category:Tin whistle",
    "Category:Cimbalom", "Category:Accordion music", "Category:Bandoneon", "Category:Cuatro",
    "Category:Audio files of traditional music", "Category:Audio files of folk music",
    "Category:Ethnographic sound recordings", "Category:Field recordings of music",
    "Category:Traditional songs", "Category:Folk songs", "Category:Audio files of world music",
]

BAD_CAT = re.compile(r"(Eurovision|anthem|national anthem|venues|events|videos|notation|sheet|"
                     r"museum|people|musicians|composers|instruments$|covers|karaoke|MIDI)", re.I)
BAD_FILE = re.compile(r"(pronunciation|speech|interview|lecture|reading|podcast|news|"
                      r"LL-Q|-ru-\.|-de-\.|-en-\.|anthem|hymn\b|test|tone|sine)", re.I)


def api(params, tries=5):
    params["format"] = "json"
    wait = 2
    for _ in range(tries):
        try:
            time.sleep(0.5)
            req = urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            print(f"   retry {wait}s: {e}", flush=True)
            time.sleep(wait); wait = min(wait * 2, 60)
    return {}


def members(cat, want_subcats=True):
    files, subs, cont = [], [], {}
    while True:
        d = api({"action": "query", "list": "categorymembers", "cmtitle": cat,
                 "cmtype": "file|subcat" if want_subcats else "file", "cmlimit": 500, **cont})
        got = d.get("query", {}).get("categorymembers")
        if got is None:
            return [], []
        for m in got:
            (subs if m["ns"] == 14 else files).append(m["title"])
        cont = d.get("continue", {})
        if not cont:
            break
    return [f for f in files if AUDIO.search(f) and not BAD_FILE.search(f)], subs


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
                        "artist": strip("Artist")[:80], "desc": strip("ImageDescription")[:200]})
    return out


def main():
    catalog = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    todo = []
    for name, iso in COUNTRIES.items():
        for pat in PATTERNS:
            todo.append((pat.format(c=name), iso))
    todo += [(c, None) for c in EXTRA]

    for cat, iso in todo:
        if cat in catalog:
            continue
        files, subs = members(cat)
        # one level down, skipping obviously irrelevant branches
        for s in subs[:25]:
            if BAD_CAT.search(s):
                continue
            f2, _ = members(s, want_subcats=False)
            files += f2
        files = list(dict.fromkeys(files))
        if not files:
            catalog[cat] = []
            continue
        rows = info(files[:400])
        for r in rows:
            r["iso"] = iso
        catalog[cat] = rows
        print(f"{len(rows):4d}  {cat}", flush=True)
        OUT.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for v in catalog.values())
    print(f"DONE {total} recordings across {sum(1 for v in catalog.values() if v)} categories")


if __name__ == "__main__":
    main()
