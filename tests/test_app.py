"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, alle Regeln, Randgrößen, Pivot-Regler, ausgeblendete Regler, Permalink, Experimente auf Abruf."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import nsx_constants as C
from nsx_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


def _run(setup=None, timeout=300):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def _step_slider(at):
    found = [s for s in at.slider if s.key == "nsx_step"]
    return found[0] if found else None


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info) + list(at.error)]


def test_default_renders_without_exception():
    at = _run()
    assert _metric(at, "Degenerierte Pivots") == ["24 von 42"] and _step_slider(at).value == 21 and _step_slider(at).max == 42
    assert any("Optimal nach 42 Pivots (24 davon degeneriert): Kosten 1 131" in t for t in _texts(at))


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert not at.error and _metric(at, "Degenerierte Pivots")


@pytest.mark.parametrize("pricing", list(C.PRICING))
@pytest.mark.parametrize("leaving", list(C.LEAVING))
def test_every_rule_combination_renders(pricing, leaving):
    def setup(at):
        at.session_state["pricing_radio"] = pricing
        at.session_state["leaving_radio"] = leaving
    at = _run(setup)
    assert not at.error and any("Optimal nach" in t for t in _texts(at))


def test_extreme_sizes_render():
    for vals in ((("plants_slider", C.PLANTS_MIN), ("dcs_slider", C.DCS_MIN), ("stores_slider", C.STORES_MIN), ("flow_slider", C.FLOW_MIN)),
                 (("plants_slider", C.PLANTS_MAX), ("dcs_slider", C.DCS_MAX), ("stores_slider", C.STORES_MAX), ("flow_slider", C.FLOW_MAX))):
        def setup(at, vals=vals):
            for key, value in vals:
                at.session_state[key] = value
        at = _run(setup)
        assert not at.error and _metric(at, "Degenerierte Pivots")


def test_pivot_slider_moves_through_frames():
    at = _run()
    top = int(_step_slider(at).max)
    for value in (1, 2, top // 2, top):
        _step_slider(at).set_value(value)
        at.run()
        assert not at.exception and _step_slider(at).value == value


def test_big_m_too_small_warns():
    at = _run(lambda a: _apply(a, C.PRESETS["⚠️ Big-M zu klein"]))
    assert any("künstliche Kanten" in t and "M = 4" in t for t in _texts(at))
    assert any("Schattenpreise gelten nur für eine zulässige Lösung" in t for t in _texts(at))


def test_hidden_controls_keep_their_values_across_a_net_switch():
    at = _run()
    at.sidebar.slider(key="plants_slider").set_value(5)
    at.run()
    at.sidebar.selectbox(key="net_select").set_value("diamond")
    at.run()
    assert not at.exception and not [w for w in at.sidebar.slider if w.key == "plants_slider"]
    at.sidebar.selectbox(key="net_select").set_value("distribution")
    at.run()
    assert at.sidebar.slider(key="plants_slider").value == 5 and not at.exception


def test_permalink_settings_are_loaded_and_clamped():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.query_params["net"] = "distribution"
    at.query_params["plants"] = "99"
    at.query_params["flow"] = "47"
    at.query_params["pricing"] = "block"
    at.query_params["leaving"] = "first"
    at.query_params["bigm"] = "25"
    at.run()
    assert not at.exception
    assert at.sidebar.slider(key="plants_slider").value == C.PLANTS_MAX and at.sidebar.slider(key="flow_slider").value == 50
    assert at.sidebar.radio(key="pricing_radio").value == "block" and at.sidebar.radio(key="leaving_radio").value == "first" and at.sidebar.radio(key="bigm_radio").value == 25


def test_invalid_permalink_values_fall_back_to_the_defaults():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.query_params["bigm"] = "7"
    at.query_params["pricing"] = "magic"
    at.run()
    assert not at.exception and at.sidebar.radio(key="bigm_radio").value == C.DEFAULT_BIG_M and at.sidebar.radio(key="pricing_radio").value == C.DEFAULT_PRICING


def test_experiments_run_on_demand(monkeypatch):
    import nsx_evaluation as ev
    s_orig, d_orig = ev.sizes, ev.distribution
    monkeypatch.setattr(ev, "sizes", lambda params: s_orig(params, sizes=((2, 2, 4), (3, 4, 8)), seeds=C.SIZE_SEEDS[:2]))
    monkeypatch.setattr(ev, "distribution", lambda params: d_orig(params, seeds=C.SWEEP_SEEDS[:3]))
    at = _run()
    for key in ("sizes_start", "dist_start"):
        next(b for b in at.button if b.key == key).click().run()
        assert not at.exception, key
    assert any("Big-M: bei 2 / 5 / 10 %" in c.value for c in at.caption)


def test_source_has_explicit_chart_keys_and_locked_axes():
    app = APP.read_text(encoding="utf-8")
    assert all(re.search(r"plotly_chart\(.*key=", line) for line in app.splitlines() if "st.plotly_chart(" in line)
    viz = (ROOT / "nsx_visualization.py").read_text(encoding="utf-8")
    assert viz.count("return _base(fig") + viz.count("return _frame(fig") >= 8 and "def lock_axes" in viz
