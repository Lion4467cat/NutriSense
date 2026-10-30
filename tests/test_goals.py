"""Daily-goal WHO values (data/goals_who.yaml) + GET /goals — spec 002 T-D (backend).

Prior art for HTTP-style assertions: tests/test_pipeline_seams.py (seams 6-7)
and tests/test_api.py. The /goals endpoint is served in the same read-only,
config-loaded style as /menu; /analyze's request and result contracts are
guarded here so the addition cannot drift them.

Values are golden-locked to docs/research/who-goals.md (§3 energy table,
§4 protein table, §6.5 WHO-default recommendation); derivations embedded in
the data file reconcile against the research file's printed row sets.
"""
import pytest
from fastapi.testclient import TestClient

import config
from config import load_goals
from engine.contract import unreadable_analysis
from main import app

client = TestClient(app)

BANDS = ["5-8", "9-11", "12-14", "15-17", "18-29", "30-59", "60-plus"]
CHILD_BANDS = BANDS[:4]
ADULT_BANDS = BANDS[4:]
SEXES = ["male", "female"]
LEVELS = ["low", "moderate", "high"]

UNITS = {"energy": "kcal_per_day", "protein": "g_per_day", "weight": "kg"}
STATUSES = {"literature", "assumed", "derived"}

# docs/research/who-goals.md §3 — golden energy table (kcal/day).
GOLDEN_ENERGY = {
    ("5-8", "male"): dict(zip(LEVELS, [1450, 1645, 1950])),
    ("5-8", "female"): dict(zip(LEVELS, [1335, 1500, 1790])),
    ("9-11", "male"): dict(zip(LEVELS, [1835, 2160, 2485])),
    ("9-11", "female"): dict(zip(LEVELS, [1700, 2000, 2300])),
    ("12-14", "male"): dict(zip(LEVELS, [2360, 2775, 3185])),
    ("12-14", "female"): dict(zip(LEVELS, [2010, 2365, 2725])),
    ("15-17", "male"): dict(zip(LEVELS, [2810, 3300, 3800])),
    ("15-17", "female"): dict(zip(LEVELS, [2125, 2500, 2875])),
    ("18-29", "male"): dict(zip(LEVELS, [2400, 2900, 3450])),
    ("18-29", "female"): dict(zip(LEVELS, [1900, 2300, 2650])),
    ("30-59", "male"): dict(zip(LEVELS, [2350, 2850, 3300])),
    ("30-59", "female"): dict(zip(LEVELS, [1850, 2250, 2650])),
    ("60-plus", "male"): dict(zip(LEVELS, [1950, 2350, 2750])),
    ("60-plus", "female"): dict(zip(LEVELS, [1700, 2050, 2350])),
}

# §4 / S2 Tables 47+46 — per-project-band protein: (g/kg/day, referent kg, g/day).
GOLDEN_PROTEIN = {
    ("5-8", "male"): (0.895, 23.9, 21.4),
    ("5-8", "female"): (0.895, 23.55, 21.1),
    ("9-11", "male"): (0.91, 36.55, 33.3),
    ("9-11", "female"): (0.905, 37.3, 33.8),
    ("12-14", "male"): (0.90, 45.0, 40.5),
    ("12-14", "female"): (0.89, 46.1, 41.0),
    ("15-17", "male"): (0.87, 66.5, 57.9),
    ("15-17", "female"): (0.84, 56.4, 47.4),
    ("18-29", "male"): (0.83, 65.0, 54.0),
    ("18-29", "female"): (0.83, 55.0, 46.0),
    ("30-59", "male"): (0.83, 65.0, 54.0),
    ("30-59", "female"): (0.83, 55.0, 46.0),
    ("60-plus", "male"): (0.83, 65.0, 54.0),
    ("60-plus", "female"): (0.83, 55.0, 46.0),
}

# §3 check block — Schofield (S1·2004·T5.2) BMR equations: slope*W + intercept.
SCHOFIELD = {
    ("male", "18-29"): (15.057, 692.2),
    ("male", "30-59"): (11.472, 873.1),
    ("male", "60-plus"): (11.711, 587.7),
    ("female", "18-29"): (14.818, 486.6),
    ("female", "30-59"): (8.126, 845.6),
    ("female", "60-plus"): (9.082, 658.5),
}
REFERENT_KG = {"male": 65.0, "female": 55.0}
PAL = {"low": 1.45, "moderate": 1.75, "high": 2.05}


def _entry(band: str, sex: str) -> dict:
    return load_goals()["bands"][band][sex]


# --- data file + loader ------------------------------------------------------

def test_goals_path_and_loader():
    assert config.GOALS_PATH.is_absolute()
    doc = load_goals()
    for key in ("bands", "activity_levels", "vocabulary", "units",
                "who_protein_s2_bands", "adult_bmr_equations", "source",
                "caveats"):
        assert key in doc, f"goals file missing {key}"


def test_loader_is_cached_and_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config.reset_caches()
    try:
        assert load_goals() is load_goals()  # cached parse
        assert "bands" in load_goals()
    finally:
        config.reset_caches()


def test_every_band_sex_and_level_is_populated():
    doc = load_goals()
    assert list(doc["bands"]) == BANDS          # project-band convention (G1)
    assert list(doc["activity_levels"]) == LEVELS
    for band in BANDS:
        for sex in SEXES:
            entry = doc["bands"][band][sex]
            for lev in LEVELS:
                kcal = entry["energy_kcal"][lev]
                assert kcal > 0 and kcal == int(kcal)
            assert entry["protein_g"] > 0
            assert 0.8 <= entry["protein_g_per_kg_day"] <= 1.0
            assert entry["referent_weight_kg"] > 0


def test_every_entry_carries_status_and_provenance():
    doc = load_goals()
    for band in BANDS:
        for sex in SEXES:
            entry = doc["bands"][band][sex]
            for nut in ("energy", "protein"):
                assert entry["status"][nut] in STATUSES
                prov = entry["provenance"][nut]
                assert prov and any(s in prov for s in ("S1", "S2")), \
                    f"{band}/{sex}/{nut} provenance must cite S1/S2"


def test_who_protein_s2_anchor_rows_are_scoped():
    s2 = load_goals()["who_protein_s2_bands"]
    for band in ("4-6", "7-10", "11-14", "15-18"):
        for sex in ("male", "female"):
            row = s2[band][sex]
            assert row["g_per_kg_day"] > 0.8
            assert row["weight_kg"] > 15
            assert row["g_per_day"] == pytest.approx(
                row["g_per_kg_day"] * row["weight_kg"], abs=0.3)
    assert s2["status"] == "literature"


# --- value-level contracts vs the research file ------------------------------

def test_energy_matches_research_table_and_rows():
    doc = load_goals()
    means = {  # §5 raw S1 row sets, per the research file's derivations
        ("5-8", "male"): {"low": (1350 + 1450 + 1550) / 3,       # rows 6-7…8-9 [G6]
                          "moderate": (1475 + 1575 + 1700 + 1825) / 4,
                          "high": (1800 + 1950 + 2100) / 3},
        ("5-8", "female"): {"low": (1225 + 1325 + 1450) / 3,
                            "moderate": (1325 + 1425 + 1550 + 1700) / 4,
                            "high": (1650 + 1775 + 1950) / 3},
        ("9-11", "male"): {"low": (1675 + 1825 + 2000) / 3,
                           "moderate": (1975 + 2150 + 2350) / 3,
                           "high": (2275 + 2475 + 2700) / 3},
        ("9-11", "female"): {"low": (1575 + 1700 + 1825) / 3,
                             "moderate": (1850 + 2000 + 2150) / 3,
                             "high": (2125 + 2300 + 2475) / 3},
        ("12-14", "male"): {"low": (2175 + 2350 + 2550) / 3,
                            "moderate": (2550 + 2775 + 3000) / 3,
                            "high": (2925 + 3175 + 3450) / 3},
        ("12-14", "female"): {"low": (1925 + 2025 + 2075) / 3,
                              "moderate": (2275 + 2375 + 2450) / 3,
                              "high": (2625 + 2725 + 2825) / 3},
        ("15-17", "male"): {"low": (2700 + 2825 + 2900) / 3,
                            "moderate": (3175 + 3325 + 3400) / 3,
                            "high": (3650 + 3825 + 3925) / 3},
        ("15-17", "female"): {"low": (2125 + 2125 + 2125) / 3,
                              "moderate": (2500 + 2500 + 2500) / 3,
                              "high": (2875 + 2875 + 2875) / 3},
    }
    for band in BANDS:
        for sex in SEXES:
            served = doc["bands"][band][sex]["energy_kcal"]
            assert served == GOLDEN_ENERGY[(band, sex)], \
                f"{band}/{sex} energy drifted from research §3"
            if band in means:  # child bands: no re-rounding beyond the file's
                for lev in LEVELS:
                    assert served[lev] == pytest.approx(
                        means[(band, sex)][lev], abs=6)


def test_adult_energy_reproduces_schofield_at_referents():
    doc = load_goals()
    for band in ADULT_BANDS:
        for sex in SEXES:
            slope, intercept = SCHOFIELD[(sex, band)]
            bmr = slope * REFERENT_KG[sex] + intercept
            served = doc["bands"][band][sex]["energy_kcal"]
            for lev in LEVELS:  # S1 rounds printed kcal/day to closest 50
                assert abs(served[lev] - bmr * PAL[lev]) <= 25.5, \
                    f"{band}/{sex}/{lev} off from S1 equation check block"


def test_protein_matches_s2_tables_and_band_derivations():
    doc = load_goals()
    s2 = doc["who_protein_s2_bands"]
    overlapped = {  # spanned project bands -> overlapped S2 rows (G7)
        "5-8": ("4-6", "7-10"),
        "9-11": ("7-10", "11-14"),
    }
    for band in BANDS:
        for sex in SEXES:
            entry = doc["bands"][band][sex]
            g_per_kg, weight, g_day = GOLDEN_PROTEIN[(band, sex)]
            assert entry["protein_g_per_kg_day"] == pytest.approx(g_per_kg, abs=1e-9)
            assert entry["referent_weight_kg"] == pytest.approx(weight)
            assert entry["protein_g"] == pytest.approx(g_day)
            if band in overlapped:
                a, b = overlapped[band]
                kg = (s2[a][sex]["g_per_kg_day"] + s2[b][sex]["g_per_kg_day"]) / 2
                w = (s2[a][sex]["weight_kg"] + s2[b][sex]["weight_kg"]) / 2
                assert g_per_kg == pytest.approx(kg)
                assert weight == pytest.approx(w)
                assert g_day == pytest.approx(round(kg * w, 1))
            if band in ADULT_BANDS:  # S2 T46: 65 kg men -> 54 g, 55 kg women -> 46
                assert abs(g_day - 0.83 * weight) <= 0.5


def test_protein_mid_childhood_rise_then_decline():
    doc = load_goals()
    for sex in SEXES:
        kg = [doc["bands"][b][sex]["protein_g_per_kg_day"] for b in BANDS]
        assert kg[1] > kg[0]                     # 7-10 y rise vs 4-6 y
        assert kg[1] >= kg[2] > kg[3] > kg[4]    # decline to adult 0.83
        for band in ADULT_BANDS:                 # S2: no adult sex/age split
            assert doc["bands"][band][sex]["protein_g_per_kg_day"] == 0.83


def test_school_bands_are_a_separate_system():
    bands = load_goals()["bands"]
    for token in ("1-5", "6-8", "9-10"):
        assert token not in bands, f"school band {token} leaked into WHO goals"


# --- shaping-choices bookkeeping ---------------------------------------------

def test_shaping_choices_recorded_not_silent():
    text = config.GOALS_PATH.read_text()
    for i in range(1, 14):
        assert f"[G{i}]" in text, f"G{i} not recorded in goals file notes"
    assert "currency check" in text.lower()
    assert "assumed" in text


def test_caveats_carry_population_and_margin_notes():
    caveats = load_goals()["caveats"]
    assert any("population" in c for c in caveats)      # G3 (S1 §5.4.1)
    assert any("margin" in c for c in caveats)          # G11


def test_adult_bmr_equations_match_s1():
    doc = load_goals()
    eqs = doc["adult_bmr_equations"]
    for sex in SEXES:
        for band in ADULT_BANDS:
            row = eqs[sex][band]
            slope, intercept = SCHOFIELD[(sex, band)]
            assert row["slope"] == slope and row["intercept"] == intercept
    assert eqs["status"] == "literature"


def test_adult_pal_factors_are_the_served_columns():
    al = load_goals()["activity_levels"]
    for lev in LEVELS:
        assert al[lev]["pal_factor"] == PAL[lev]
        assert al[lev]["status"] == "literature"


# --- GET /goals ---------------------------------------------------------------

def test_goals_endpoint_shape():
    r = client.get("/goals")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"age_bands", "sexes", "activity_levels", "units",
                         "daily", "source", "caveats"}
    assert body["age_bands"] == BANDS
    assert body["sexes"] == SEXES
    assert body["activity_levels"] == LEVELS
    assert body["units"] == UNITS
    doc = load_goals()
    for band in BANDS:
        for sex in SEXES:
            assert body["daily"][band][sex] == doc["bands"][band][sex]
    assert body["caveats"] == doc["caveats"]
    assert "2026" in body["source"]["verified"]


def test_goals_endpoint_covers_every_profile():
    r = client.get("/goals")
    assert r.status_code == 200
    daily = r.json()["daily"]
    for band in BANDS:
        for sex in SEXES:
            prof = daily[band][sex]
            assert prof["energy_kcal"] == GOLDEN_ENERGY[(band, sex)]
            assert prof["protein_g"] == GOLDEN_PROTEIN[(band, sex)][2]


# --- /analyze contracts are untouched by /goals --------------------------------

def test_analyze_result_contract_unchanged():
    r = client.post("/analyze",
                    files={"file": ("bad.jpg", b"not an image", "image/jpeg")},
                    data={"day": "mon", "band": "1-5"})
    assert r.status_code == 200
    wire = unreadable_analysis().to_wire()
    body = r.json()
    assert body == wire            # exact envelope equality, key-for-key
    assert body["verdict"] == "cannot_verify"
    assert body["path_used"] is None
    assert body["failures"][0]["kind"] == "input_unreadable"


def test_analyze_request_contract_unchanged():
    r = client.post("/analyze",
                    files={"file": ("bad.jpg", b"not an image", "image/jpeg")},
                    data={"day": "mon"})          # band omitted
    assert r.status_code == 422
    locs = [e["loc"] for e in r.json()["detail"]]
    assert any("band" in loc for loc in locs)
