"""Presets: vollständig, in den Grenzen, und jedes Beispiel zeigt, was sein Hilfetext behauptet."""

import pytest

import nsx_constants as C
import nsx_evaluation as ev
import nsx_presets as P

KEYS = set(P.PRESET_KEYS)


def _params(p):
    return ev.Params(p["net"], p["plants"], p["dcs"], p["stores"], p["flow"], p["pricing"], p["leaving"], p["big_m"], p["seed"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["pricing"] in C.PRICING and p["leaving"] in C.LEAVING and p["big_m"] in C.BIG_M_PCTS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["flow"] - C.FLOW_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_first_preset():
    assert _params(C.PRESETS["🚚 Distributionsnetz"]) == ev.DEFAULT_PARAMS


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"💎 Raute", "🧩 Zuordnung"}


def test_permalink_casts_accept_only_valid_values():
    spec = P.SETTING_SPECS
    assert spec["bigm_radio"].caster("10") == 10
    for key, bad in (("bigm_radio", "7"), ("pricing_radio", "magic"), ("leaving_radio", "x")):
        with pytest.raises(ValueError):
            spec[key].caster(bad)


def test_the_presets_show_both_good_and_bad_news():
    """Gut: jedes Preset außer Big-M zu klein findet dieselben Kosten wie Successive Shortest Paths; schlecht: Big-M zu klein bleibt unzulässig, die erste Austrittskante verliert die starke Zulässigkeit."""
    for name, p in C.PRESETS.items():
        a = ev.analyse(_params(p))
        assert a["match"] == (name != "⚠️ Big-M zu klein"), name
    lv = ev.compare_leaving(_params(C.PRESETS["↩️ Erste Austrittskante"]))
    assert lv["leaving"]["first"]["violations"] > 0 and lv["leaving"]["strong"]["violations"] == 0
