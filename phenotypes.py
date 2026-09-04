"""
Phenotype -> geography mapping.

DeepFace's race model outputs six coarse phenotype buckets. For each bucket we
keep a hand-made table of ISO-3166 alpha-3 country codes -> how common that
phenotype is in that country (0..1). The final heat map is the probability-
weighted blend of these tables, so a face that scores 55% "white" / 40%
"middle eastern" lights up the Mediterranean and Levant rather than Scandinavia.

This is a playful toy, not anthropology. Phenotype != ancestry != nationality.
"""

CATEGORIES = ["asian", "southeast asian", "indian", "black", "white", "middle eastern", "latino hispanic"]

LABELS = {
    "asian": "East Asian",
    "southeast asian": "Southeast Asian",
    "indian": "South Asian",
    "black": "Sub-Saharan African",
    "white": "European",
    "middle eastern": "Middle Eastern / North African",
    "latino hispanic": "Latin American / Mestizo",
}

# Nicer names when two buckets are both strong. Keys are frozensets of two categories.
BLEND_LABELS = {
    frozenset({"asian", "southeast asian"}): "East / Southeast Asian",
    frozenset({"southeast asian", "indian"}): "Indo-Malay / Burmese",
    frozenset({"southeast asian", "latino hispanic"}): "Filipino / Pacific Mestizo",
    frozenset({"southeast asian", "black"}): "Melanesian / Austronesian",
    frozenset({"southeast asian", "white"}): "Eurasian / Southeast Asian",
    frozenset({"southeast asian", "middle eastern"}): "Malay / Arab-Asian",
    frozenset({"white", "middle eastern"}): "Mediterranean / Levantine",
    frozenset({"white", "asian"}): "Eurasian / Central Asian",
    frozenset({"white", "latino hispanic"}): "Southern European / Latin",
    frozenset({"white", "indian"}): "Indo-Iranian / Persianate",
    frozenset({"white", "black"}): "Afro-European / Creole",
    frozenset({"middle eastern", "indian"}): "Persian / Pashtun / Pakistani",
    frozenset({"middle eastern", "asian"}): "Turkic / Central Asian",
    frozenset({"middle eastern", "black"}): "Horn of Africa / Sahel",
    frozenset({"middle eastern", "latino hispanic"}): "Mediterranean / Latin",
    frozenset({"asian", "indian"}): "Himalayan / Northeast Indian",
    frozenset({"asian", "latino hispanic"}): "Indigenous American / Andean",
    frozenset({"asian", "black"}): "Melanesian / Afro-Asian",
    frozenset({"indian", "black"}): "Indo-African / Swahili Coast",
    frozenset({"indian", "latino hispanic"}): "Indo-Caribbean",
    frozenset({"black", "latino hispanic"}): "Afro-Caribbean / Afro-Latino",
}

# Which procedural music profile the frontend should play.
MUSIC_FOR_CATEGORY = {
    "asian": "east_asian",
    "southeast asian": "southeast_asian",
    "indian": "south_asian",
    "black": "west_african",
    "white": "european",
    "middle eastern": "mena",
    "latino hispanic": "latin",
}
MUSIC_FOR_BLEND = {
    frozenset({"asian", "latino hispanic"}): "andean",
    frozenset({"white", "middle eastern"}): "mediterranean",
    frozenset({"middle eastern", "latino hispanic"}): "mediterranean",
    frozenset({"white", "latino hispanic"}): "mediterranean",
    frozenset({"middle eastern", "black"}): "sahel",
    frozenset({"white", "asian"}): "eurasian",
    frozenset({"middle eastern", "asian"}): "eurasian",
}

# If the single hottest country is one of these, its regional sound wins over the bucket default.
MUSIC_FOR_TOP_COUNTRY = {
    "GEO": "caucasus", "ARM": "caucasus", "AZE": "caucasus",
    "PER": "andean", "BOL": "andean", "ECU": "andean",
    "MLI": "sahel", "NER": "sahel", "MRT": "sahel",
    "KAZ": "eurasian", "KGZ": "eurasian", "MNG": "eurasian", "UZB": "eurasian", "TKM": "eurasian",
}

# Natural Earth ADM0_A3 codes. Anything not listed counts as 0 for that bucket.
COUNTRY_WEIGHTS = {
    "asian": {
        "CHN": 1.0, "JPN": 1.0, "KOR": 1.0, "PRK": 1.0, "TWN": 1.0, "MNG": 0.9,
        "VNM": 0.55, "THA": 0.35, "MMR": 0.3, "SGP": 0.7, "MYS": 0.3,
        "BTN": 0.7, "NPL": 0.35, "KAZ": 0.5, "KGZ": 0.6, "UZB": 0.35, "TJK": 0.25,
        "TKM": 0.3, "RUS": 0.2, "IND": 0.1, "BGD": 0.05,
        "USA": 0.1, "CAN": 0.1, "AUS": 0.1, "NZL": 0.1, "PER": 0.15, "BOL": 0.15,
        "GTM": 0.15, "MEX": 0.1, "GRL": 0.5, "ECU": 0.1,
    },
    "southeast asian": {
        "IDN": 1.0, "PHL": 1.0, "MYS": 0.95, "THA": 0.95, "VNM": 0.9, "KHM": 1.0,
        "LAO": 1.0, "MMR": 0.9, "BRN": 0.9, "TLS": 0.9, "SGP": 0.6, "PNG": 0.4,
        "FJI": 0.3, "SLB": 0.25, "VUT": 0.25, "MDG": 0.4, "TWN": 0.15, "CHN": 0.1,
        "IND": 0.05, "BGD": 0.1, "LKA": 0.05, "USA": 0.05, "AUS": 0.05,
    },
    "indian": {
        "IND": 1.0, "PAK": 0.95, "BGD": 0.95, "LKA": 0.95, "NPL": 0.9, "BTN": 0.4,
        "MDV": 0.8, "AFG": 0.55, "MMR": 0.15, "MYS": 0.15, "SGP": 0.15, "FJI": 0.35,
        "GUY": 0.4, "TTO": 0.4, "SUR": 0.3, "MUS": 0.5, "ARE": 0.3, "QAT": 0.3,
        "KWT": 0.2, "OMN": 0.2, "BHR": 0.2, "SAU": 0.15, "GBR": 0.1, "ZAF": 0.05,
        "KEN": 0.05, "TZA": 0.05, "UGA": 0.05, "IRN": 0.1,
    },
    "black": {
        "NGA": 1.0, "GHA": 1.0, "SEN": 1.0, "MLI": 0.95, "CIV": 1.0, "LBR": 1.0,
        "SLE": 1.0, "GIN": 1.0, "GNB": 1.0, "GMB": 1.0, "BFA": 1.0, "NER": 0.9,
        "TCD": 0.85, "CMR": 1.0, "COD": 1.0, "COG": 1.0, "GAB": 1.0, "GNQ": 1.0,
        "CAF": 1.0, "SDS": 1.0, "SSD": 1.0, "SDN": 0.6, "ETH": 0.9, "ERI": 0.85,
        "SOM": 0.85, "SOL": 0.85, "DJI": 0.85, "KEN": 1.0, "UGA": 1.0, "TZA": 1.0,
        "RWA": 1.0, "BDI": 1.0, "MOZ": 1.0, "MWI": 1.0, "ZMB": 1.0, "ZWE": 1.0,
        "AGO": 1.0, "NAM": 0.85, "BWA": 0.9, "ZAF": 0.8, "LSO": 1.0, "SWZ": 1.0,
        "MDG": 0.6, "TGO": 1.0, "BEN": 1.0, "MRT": 0.5, "HTI": 0.95, "JAM": 0.95,
        "BHS": 0.85, "TTO": 0.4, "DOM": 0.4, "CUB": 0.35, "PRI": 0.25, "USA": 0.25,
        "BRA": 0.35, "COL": 0.15, "VEN": 0.1, "PAN": 0.15, "GUY": 0.3, "SUR": 0.35,
        "BLZ": 0.3, "GBR": 0.05, "FRA": 0.05, "SAH": 0.2, "ESH": 0.2, "LBY": 0.1,
        "EGY": 0.1, "DZA": 0.05, "MAR": 0.05, "YEM": 0.1, "SAU": 0.1, "PNG": 0.35,
        "SLB": 0.4, "VUT": 0.4, "AUS": 0.05,
    },
    "white": {
        "GBR": 1.0, "IRL": 1.0, "FRA": 1.0, "DEU": 1.0, "NLD": 1.0, "BEL": 1.0,
        "LUX": 1.0, "CHE": 1.0, "AUT": 1.0, "DNK": 1.0, "SWE": 1.0, "NOR": 1.0,
        "FIN": 1.0, "ISL": 1.0, "POL": 1.0, "CZE": 1.0, "SVK": 1.0, "HUN": 1.0,
        "ROU": 1.0, "BGR": 1.0, "SRB": 1.0, "HRV": 1.0, "SVN": 1.0, "BIH": 1.0,
        "MNE": 1.0, "MKD": 1.0, "ALB": 0.9, "GRC": 0.9, "ITA": 0.95, "ESP": 0.95,
        "PRT": 0.95, "EST": 1.0, "LVA": 1.0, "LTU": 1.0, "BLR": 1.0, "UKR": 1.0,
        "MDA": 1.0, "RUS": 0.9, "CYP": 0.8, "CYN": 0.7, "MLT": 0.85, "KOS": 0.9,
        "USA": 0.75, "CAN": 0.8, "AUS": 0.8, "NZL": 0.75, "ARG": 0.8, "URY": 0.85,
        "CHL": 0.55, "BRA": 0.45, "ZAF": 0.15, "ISR": 0.6, "TUR": 0.55, "GEO": 0.7,
        "ARM": 0.7, "AZE": 0.4, "KAZ": 0.35, "LBN": 0.4, "SYR": 0.3, "IRN": 0.3,
        "MAR": 0.1, "TUN": 0.15, "DZA": 0.1, "CUB": 0.4, "CRI": 0.4, "VEN": 0.35,
        "COL": 0.3, "MEX": 0.2, "PRI": 0.4, "GRL": 0.3, "FLK": 0.9,
    },
    "middle eastern": {
        "SAU": 1.0, "YEM": 0.9, "OMN": 0.95, "ARE": 0.95, "QAT": 0.95, "KWT": 0.95,
        "BHR": 0.95, "IRQ": 1.0, "SYR": 1.0, "LBN": 1.0, "JOR": 1.0, "ISR": 0.85,
        "PSE": 1.0, "PSX": 1.0, "TUR": 0.9, "IRN": 1.0, "AFG": 0.6, "AZE": 0.7,
        "ARM": 0.5, "GEO": 0.4, "EGY": 0.9, "LBY": 0.9, "TUN": 0.9, "DZA": 0.9,
        "MAR": 0.9, "ESH": 0.7, "SAH": 0.7, "SDN": 0.4, "CYP": 0.5, "CYN": 0.6,
        "GRC": 0.35, "ALB": 0.2, "MKD": 0.15, "BIH": 0.15, "PAK": 0.3, "TJK": 0.4,
        "UZB": 0.35, "TKM": 0.4, "KGZ": 0.15, "ITA": 0.2, "ESP": 0.2, "MLT": 0.35,
        "BGR": 0.1, "SRB": 0.05, "MRT": 0.4, "SOM": 0.2, "SOL": 0.2, "DJI": 0.2,
        "ETH": 0.15, "ERI": 0.2, "IND": 0.05, "USA": 0.05, "FRA": 0.1, "DEU": 0.05,
        "SWE": 0.05, "ARG": 0.1, "BRA": 0.1, "CHL": 0.1, "MEX": 0.05, "KOS": 0.1,
    },
    "latino hispanic": {
        "MEX": 1.0, "GTM": 0.9, "HND": 0.95, "SLV": 1.0, "NIC": 1.0, "CRI": 0.85,
        "PAN": 0.9, "COL": 1.0, "VEN": 1.0, "ECU": 0.95, "PER": 0.9, "BOL": 0.85,
        "PRY": 1.0, "CHL": 0.85, "ARG": 0.7, "URY": 0.6, "BRA": 0.9, "CUB": 0.8,
        "DOM": 0.85, "PRI": 0.9, "HTI": 0.2, "BLZ": 0.6, "GUY": 0.3, "SUR": 0.3,
        "USA": 0.4, "ESP": 0.5, "PRT": 0.45, "ITA": 0.3, "PHL": 0.35, "GRC": 0.1,
        "FRA": 0.05, "TTO": 0.15, "JAM": 0.1,
    },
}


def blend_heatmap(probs: dict[str, float]) -> dict[str, float]:
    """probs: category -> 0..1 (sums to ~1). Returns ISO3 -> 0..1 heat, max normalised to 1."""
    heat: dict[str, float] = {}
    for cat, p in probs.items():
        if p <= 0:
            continue
        for iso, w in COUNTRY_WEIGHTS.get(cat, {}).items():
            heat[iso] = heat.get(iso, 0.0) + p * w
    top = max(heat.values(), default=1.0) or 1.0
    return {iso: round(v / top, 4) for iso, v in heat.items()}


def describe(probs: dict[str, float], heat: dict[str, float] | None = None) -> dict:
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    (c1, p1), (c2, p2) = ranked[0], ranked[1]
    pair = frozenset({c1, c2})
    is_blend = p2 >= 0.25 and p2 >= 0.55 * p1
    if is_blend and pair in BLEND_LABELS:
        label = BLEND_LABELS[pair]
        music = MUSIC_FOR_BLEND.get(pair, MUSIC_FOR_CATEGORY[c1])
    else:
        label = LABELS[c1]
        music = MUSIC_FOR_CATEGORY[c1]
    if heat:
        top_iso = max(heat, key=heat.get)
        music = MUSIC_FOR_TOP_COUNTRY.get(top_iso, music)
    confidence = "high" if p1 >= 0.7 else "medium" if p1 >= 0.45 else "low"
    return {
        "label": label,
        "primary": c1,
        "secondary": c2 if is_blend else None,
        "confidence": confidence,
        "music": music,
    }
