"""
IllustrativeDNA-style population taxonomy on top of the seven FairFace macro groups.

Each population has: the macro group it belongs to, a display name, a music profile,
and country weights (ADM0_A3 -> 0..1 "how common this population is there").

Within a macro group, the split between populations comes from a refiner (vision LLM)
when one is configured, otherwise from `heuristic_split`, which nudges the split using
the *other* macro probabilities (a European face with a strong Middle-Eastern signal is
pushed toward Southern European / Balkan rather than Nordic, etc.).
"""

# population id -> dict(macro, name, music, countries)
POPULATIONS = {
    # ---------------- European ----------------
    "nw_european": dict(macro="white", name="Northwestern European", music="european",
        countries={"GBR": 1, "IRL": 1, "FRA": 0.8, "NLD": 1, "BEL": 1, "LUX": 1, "DEU": 0.6, "CHE": 0.6, "DNK": 0.7, "CAN": 0.3, "AUS": 0.3, "NZL": 0.3, "ZAF": 0.07}),
    "nordic": dict(macro="white", name="Nordic & Finnic", music="european",
        countries={"SWE": 1, "NOR": 1, "FIN": 1, "ISL": 1, "DNK": 0.8, "EST": 0.7}),
    "central_european": dict(macro="white", name="Central European", music="european",
        countries={"DEU": 1, "AUT": 1, "CHE": 0.8, "CZE": 1, "SVK": 0.9, "HUN": 0.9, "SVN": 0.8, "POL": 0.7,
                   "NLD": 0.3, "ARG": 0.1, "BRA": 0.1}),
    "east_european": dict(macro="white", name="Eastern European & Slavic", music="european",
        countries={"POL": 1, "UKR": 1, "BLR": 1, "RUS": 1, "LTU": 0.9, "LVA": 0.9, "EST": 0.5, "MDA": 0.8,
                   "SVK": 0.5, "CZE": 0.4, "KAZ": 0.4, "ISR": 0.15}),
    "south_european": dict(macro="white", name="Southern European (Italian & Iberian)", music="mediterranean",
        countries={"ITA": 1, "ESP": 1, "PRT": 1, "FRA": 0.4, "MLT": 0.8, "ARG": 0.4, "URY": 0.4, "BRA": 0.25,
                   "CHL": 0.2, "VEN": 0.15}),
    "balkan": dict(macro="white", name="Balkan & Aegean", music="mediterranean",
        countries={"GRC": 1, "ALB": 1, "SRB": 1, "BIH": 1, "HRV": 0.9, "MKD": 1, "MNE": 1, "BGR": 1, "KOS": 1,
                   "ROU": 0.8, "SVN": 0.4, "CYP": 0.7, "TUR": 0.25, "ITA": 0.15, "HUN": 0.2}),
    # ---------------- Middle East / North Africa ----------------
    "anatolian": dict(macro="middle eastern", name="Anatolian", music="mena",
        countries={"TUR": 1, "CYP": 0.5, "CYN": 0.9, "GRC": 0.2, "BGR": 0.15, "AZE": 0.3, "DEU": 0.1, "SYR": 0.15, "IRQ": 0.1}),
    "caucasus": dict(macro="middle eastern", name="Caucasus", music="caucasus",
        countries={"GEO": 1, "ARM": 1, "AZE": 1, "RUS": 0.15, "TUR": 0.25, "IRN": 0.15}),
    "levantine": dict(macro="middle eastern", name="Levantine", music="mena",
        countries={"LBN": 1, "SYR": 1, "JOR": 1, "PSX": 1, "ISR": 0.35, "CYP": 0.3, "IRQ": 0.3, "TUR": 0.2, "EGY": 0.15}),
    "mesopotamian": dict(macro="middle eastern", name="Mesopotamian & Gulf", music="mena",
        countries={"IRQ": 1, "KWT": 1, "BHR": 0.9, "QAT": 0.8, "ARE": 0.7, "SAU": 0.6, "IRN": 0.3, "SYR": 0.3}),
    "arabian": dict(macro="middle eastern", name="Arabian Peninsula", music="mena",
        countries={"SAU": 1, "YEM": 1, "OMN": 1, "ARE": 0.8, "QAT": 0.7, "KWT": 0.6, "BHR": 0.6, "JOR": 0.4, "SDN": 0.2, "ERI": 0.15}),
    "iranian": dict(macro="middle eastern", name="Iranian Plateau", music="mena",
        countries={"IRN": 1, "AFG": 0.9, "TJK": 0.9, "UZB": 0.4, "AZE": 0.3, "IRQ": 0.3, "PAK": 0.3, "TKM": 0.4}),
    "maghrebi": dict(macro="middle eastern", name="Maghrebi (North African)", music="mena",
        countries={"MAR": 1, "DZA": 1, "TUN": 1, "LBY": 0.9, "MRT": 0.6, "ESH": 0.9, "SAH": 0.9, "FRA": 0.15, "ESP": 0.1, "MLT": 0.2}),
    "egyptian": dict(macro="middle eastern", name="Egyptian & Nile Valley", music="mena",
        countries={"EGY": 1, "SDN": 0.7, "LBY": 0.3, "SDS": 0.1, "SSD": 0.1}),
    # ---------------- South Asia ----------------
    "north_indian": dict(macro="indian", name="North Indian (Indo-Aryan)", music="south_asian",
        countries={"IND": 1, "NPL": 0.9, "PAK": 0.7, "BGD": 0.6, "BTN": 0.3, "GBR": 0.1, "ARE": 0.2}),
    "south_indian": dict(macro="indian", name="South Indian (Dravidian)", music="south_asian",
        countries={"IND": 1, "LKA": 1, "MDV": 0.8, "MYS": 0.2, "SGP": 0.2, "MUS": 0.5, "FJI": 0.4, "GUY": 0.4, "TTO": 0.4, "ARE": 0.2}),
    "pashtun_pakistani": dict(macro="indian", name="Pakistani & Pashtun", music="south_asian",
        countries={"PAK": 1, "AFG": 0.8, "IND": 0.3, "IRN": 0.2, "GBR": 0.1}),
    "bengali": dict(macro="indian", name="Bengali & Eastern Indian", music="south_asian",
        countries={"BGD": 1, "IND": 0.6, "MMR": 0.2, "NPL": 0.2}),
    # ---------------- East Asia ----------------
    "east_asian": dict(macro="asian", name="Northeast Asian (Han / Korean / Japanese)", music="east_asian",
        countries={"CHN": 1, "JPN": 1, "KOR": 1, "PRK": 1, "TWN": 1, "SGP": 0.6, "VNM": 0.3, "MYS": 0.3}),
    "central_asian": dict(macro="asian", name="Central Asian (Turkic & Mongolic)", music="eurasian",
        countries={"MNG": 1, "KAZ": 1, "KGZ": 1, "UZB": 0.7, "TKM": 0.6, "CHN": 0.15, "RUS": 0.2, "AFG": 0.2}),
    "himalayan": dict(macro="asian", name="Tibetan & Himalayan", music="south_asian",
        countries={"BTN": 1, "NPL": 0.7, "CHN": 0.15, "IND": 0.1, "MMR": 0.2}),
    "siberian": dict(macro="asian", name="Siberian & Arctic", music="eurasian",
        countries={"RUS": 0.5, "GRL": 1, "MNG": 0.3}),
    # ---------------- Southeast Asia / Pacific ----------------
    "mainland_sea": dict(macro="southeast asian", name="Mainland Southeast Asian", music="southeast_asian",
        countries={"VNM": 1, "THA": 1, "KHM": 1, "LAO": 1, "MMR": 1, "MYS": 0.3, "CHN": 0.1}),
    "austronesian": dict(macro="southeast asian", name="Maritime Southeast Asian (Austronesian)", music="southeast_asian",
        countries={"IDN": 1, "PHL": 1, "MYS": 1, "BRN": 1, "TLS": 0.9, "SGP": 0.5, "MDG": 0.5, "TWN": 0.15}),
    "melanesian": dict(macro="southeast asian", name="Melanesian & Pacific Islander", music="southeast_asian",
        countries={"PNG": 1, "SLB": 1, "VUT": 1, "FJI": 0.9, "TLS": 0.3, "IDN": 0.2, "NCL": 0.8}),
    # ---------------- Sub-Saharan Africa ----------------
    "west_african": dict(macro="black", name="West African", music="west_african",
        countries={"NGA": 1, "GHA": 1, "SEN": 1, "MLI": 0.9, "CIV": 1, "LBR": 1, "SLE": 1, "GIN": 1, "GNB": 1, "GMB": 1,
                   "BFA": 1, "TGO": 1, "BEN": 1, "NER": 0.8, "MRT": 0.4, "CMR": 0.5}),
    "central_african": dict(macro="black", name="Central African (Bantu)", music="west_african",
        countries={"COD": 1, "COG": 1, "GAB": 1, "GNQ": 1, "CAF": 1, "CMR": 0.9, "AGO": 0.9, "TCD": 0.7, "ZMB": 0.5}),
    "east_african": dict(macro="black", name="East African & Nilotic", music="west_african",
        countries={"KEN": 1, "UGA": 1, "TZA": 1, "RWA": 1, "BDI": 1, "SDS": 1, "SSD": 1, "SDN": 0.5, "ETH": 0.4, "MOZ": 0.5, "MWI": 0.6, "ZMB": 0.5}),
    "horn_african": dict(macro="black", name="Horn of Africa (Cushitic)", music="sahel",
        countries={"ETH": 1, "ERI": 1, "SOM": 1, "SOL": 1, "DJI": 1, "SDN": 0.5, "KEN": 0.2, "YEM": 0.2}),
    "sahelian": dict(macro="black", name="Sahelian (Fulani / Tuareg / Songhai)", music="sahel",
        countries={"MLI": 1, "NER": 1, "MRT": 0.9, "TCD": 0.8, "BFA": 0.5, "SEN": 0.5, "NGA": 0.4, "SDN": 0.4, "DZA": 0.1, "LBY": 0.1}),
    "southern_african": dict(macro="black", name="Southern African", music="west_african",
        countries={"ZAF": 0.5, "ZWE": 1, "BWA": 1, "NAM": 1, "LSO": 1, "SWZ": 1, "MOZ": 0.8, "ZMB": 0.6, "MWI": 0.6, "AGO": 0.4, "MDG": 0.3}),
    "african_diaspora": dict(macro="black", name="African Diaspora (Caribbean & Americas)", music="west_african",
        countries={"USA": 0.4, "HTI": 1, "JAM": 1, "BHS": 1, "TTO": 0.6, "DOM": 0.6, "CUB": 0.5, "PRI": 0.3, "BRA": 0.6,
                   "COL": 0.3, "PAN": 0.3, "GUY": 0.4, "SUR": 0.4, "BLZ": 0.4, "GBR": 0.1, "FRA": 0.1}),
    # ---------------- Latin America ----------------
    "mesoamerican": dict(macro="latino hispanic", name="Mesoamerican & Mexican", music="latin",
        countries={"USA": 0.25, "MEX": 1, "GTM": 1, "HND": 1, "SLV": 1, "NIC": 1, "BLZ": 0.7, "CRI": 0.5}),
    "andean": dict(macro="latino hispanic", name="Andean & Indigenous American", music="andean",
        countries={"PER": 1, "BOL": 1, "ECU": 1, "COL": 0.5, "CHL": 0.4, "PRY": 0.6, "GTM": 0.4, "MEX": 0.3, "ARG": 0.2}),
    "caribbean_hispanic": dict(macro="latino hispanic", name="Caribbean Hispanic", music="latin",
        countries={"CUB": 1, "DOM": 1, "PRI": 1, "VEN": 0.7, "COL": 0.7, "PAN": 0.8}),
    "southern_cone": dict(macro="latino hispanic", name="Southern Cone & Brazilian", music="latin",
        countries={"ARG": 1, "URY": 1, "CHL": 0.8, "BRA": 1, "PRY": 0.6, "ESP": 0.2, "PRT": 0.2, "ITA": 0.1}),
}

MACROS = ["asian", "southeast asian", "indian", "black", "white", "middle eastern", "latino hispanic"]
BY_MACRO = {m: [k for k, v in POPULATIONS.items() if v["macro"] == m] for m in MACROS}


def _norm(d):
    s = sum(d.values()) or 1.0
    return {k: v / s for k, v in d.items()}


def heuristic_split(macro: dict[str, float]) -> dict[str, dict[str, float]]:
    """Per-macro share tables {macro: {population: share}} (each table sums to 1), shaped by the
    other macro signals. A population may appear under more than one macro: FairFace's
    'White' class absorbs most Caucasus / Anatolian / Levantine faces, so those draw from it too."""
    m = {k: macro.get(k, 0.0) for k in MACROS}
    eps = 1e-6

    def rel(other, own):  # how strong `other` is relative to `own`, clipped 0..1
        return min(1.0, m[other] / (m[own] + eps)) if m[own] > 0.02 else 0.0

    s = {}
    # European: FairFace under-reports 'middle eastern', so even a faint signal is meaningful.
    me = min(1.0, 3.0 * rel("middle eastern", "white"))
    t = min(1.0, me + rel("latino hispanic", "white"))
    ea = min(1.0, rel("asian", "white"))
    s["white"] = _norm({"nw_european": (0.30 * (1 - t) + 0.04) * (1 - 0.6 * ea), "nordic": (0.10 * (1 - t) + 0.01) * (1 - 0.5 * ea),
                        "central_european": (0.22 * (1 - t) + 0.05) * (1 - 0.4 * ea), "east_european": 0.18 * (1 - t) + 0.05 + 0.25 * ea,
                        "south_european": 0.14 + 0.45 * t, "balkan": 0.06 + 0.22 * t,
                        "caucasus": 0.01 + 0.30 * me, "anatolian": 0.01 + 0.25 * me, "levantine": 0.005 + 0.12 * me})
    # Middle East: European signal -> Anatolia/Caucasus/Levant; African -> Egypt/Arabia/Maghreb; Indian -> Iran
    w, b, i = rel("white", "middle eastern"), rel("black", "middle eastern"), rel("indian", "middle eastern")
    s["middle eastern"] = _norm({"anatolian": 0.14 + 0.25 * w, "caucasus": 0.08 + 0.20 * w, "levantine": 0.16 + 0.15 * w,
                    "mesopotamian": 0.12 + 0.05 * i, "arabian": 0.12 + 0.20 * b, "iranian": 0.12 + 0.30 * i,
                    "maghrebi": 0.14 + 0.15 * b, "egyptian": 0.12 + 0.25 * b})
    # South Asia
    me, ea = rel("middle eastern", "indian"), rel("asian", "indian") + rel("southeast asian", "indian")
    s["indian"] = _norm({"north_indian": 0.40 + 0.1 * me, "south_indian": 0.30, "pashtun_pakistani": 0.15 + 0.35 * me,
                         "bengali": 0.15 + 0.30 * min(1.0, ea)})
    # East Asia
    wa, ia = rel("white", "asian") + rel("middle eastern", "asian"), rel("indian", "asian")
    wa = min(1.0, wa)
    s["asian"] = _norm({"east_asian": 0.75 * (1 - 0.7 * wa), "central_asian": 0.10 + 1.30 * wa, "himalayan": 0.08 + 0.3 * ia,
                        "siberian": 0.05 + 0.15 * wa})
    # Southeast Asia
    bs = rel("black", "southeast asian")
    s["southeast asian"] = _norm({"mainland_sea": 0.45 + 0.2 * rel("asian", "southeast asian"), "austronesian": 0.45,
                                  "melanesian": 0.10 + 0.5 * bs})
    # Sub-Saharan Africa
    mb, wb, lb = rel("middle eastern", "black"), rel("white", "black"), rel("latino hispanic", "black")
    s["black"] = _norm({"west_african": 0.30, "central_african": 0.18, "east_african": 0.15,
                        "horn_african": 0.08 + 0.35 * mb, "sahelian": 0.07 + 0.2 * mb, "southern_african": 0.12,
                        "african_diaspora": 0.10 + 0.4 * min(1.0, wb + lb)})
    # Latin America
    al, bl, wl = rel("asian", "latino hispanic") + rel("southeast asian", "latino hispanic"), rel("black", "latino hispanic"), rel("white", "latino hispanic")
    s["latino hispanic"] = _norm({"mesoamerican": 0.35, "andean": 0.20 + 0.4 * min(1.0, al), "caribbean_hispanic": 0.20 + 0.35 * bl,
                                  "southern_cone": 0.25 + 0.4 * wl})
    return s


def combine(macro: dict[str, float], split: dict[str, dict[str, float]]) -> dict[str, float]:
    """Population probabilities = sum over macros of (macro prob x that macro's share table)."""
    out = {pop: 0.0 for pop in POPULATIONS}
    for m, table in split.items():
        for pop, share in table.items():
            out[pop] += macro.get(m, 0.0) * share
    return _norm(out)


def heatmap(pops: dict[str, float], sharpen: float = 2.0) -> dict[str, float]:
    """Country heat = the strongest single population's (prob^sharpen x country weight). Using the max
    rather than a sum stops countries that sit in many populations (Poland, Germany, the USA) from piling
    up small contributions from a diffuse result."""
    heat: dict[str, float] = {}
    for pop, p in pops.items():
        if p < 0.005:
            continue
        ps = p ** sharpen
        for iso, w in POPULATIONS[pop]["countries"].items():
            heat[iso] = max(heat.get(iso, 0.0), ps * w)
    top = max(heat.values(), default=1.0) or 1.0
    return {iso: round(v / top, 4) for iso, v in heat.items()}


def label(pops: dict[str, float]) -> tuple[str, str, str]:
    """(label, primary population id, confidence)."""
    ranked = sorted(pops.items(), key=lambda kv: kv[1], reverse=True)
    (p1, v1), (p2, v2) = ranked[0], ranked[1]
    name = POPULATIONS[p1]["name"]
    if v2 >= 0.6 * v1 and v2 >= 0.12:
        name = f"{POPULATIONS[p1]['name']} / {POPULATIONS[p2]['name']}"
    conf = "high" if v1 >= 0.45 else "medium" if v1 >= 0.25 else "low"
    return name, p1, conf


def as_list(pops: dict[str, float], n: int = 8) -> list[dict]:
    ranked = sorted(pops.items(), key=lambda kv: kv[1], reverse=True)
    return [{"id": k, "name": POPULATIONS[k]["name"], "macro": POPULATIONS[k]["macro"], "pct": round(v * 100, 1)}
            for k, v in ranked[:n] if v >= 0.01]


def refiner_catalog() -> list[dict]:
    """What a vision-LLM refiner is asked to score."""
    return [{"id": k, "name": v["name"], "group": v["macro"]} for k, v in POPULATIONS.items()]
