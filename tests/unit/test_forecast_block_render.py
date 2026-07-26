"""
Unit test — ui/forecast_block.py render states + D-1 axis-position math
(05-07-PLAN.md Task 2, 05-UI-SPEC.md §Visuals — Forecast Section Contract).

The forecast block is a cache-only Streamlit render. To exercise it without a
Streamlit runtime, a small capture harness monkeypatches the module-level `st`
with a fake that records every markdown / caption / container / expander call.
The five render states are driven from the two 05-01 committed fixture records
(swiggy = full covered band; hyundai = abstain) plus a synthetic GmpRecord.

Invariants pinned here (the honesty contract):
  - full: band + GMP marker + labeled gap + always-visible metrics strip + link;
  - covered-no-GMP: band renders, marker + gap line omitted, honest no-gap note;
  - abstain: honest note, NO band, NO fabricated metric;
  - not-covered: honest note, NO band;
  - error: amber .drhp-refusal (NOT red);
  - the plot is EXACTLY ONE st.markdown (no split div);
  - the metrics strip is never behind an expander (L5-3);
  - the median never renders Display-size (P21);
  - deterministic axis-domain math (D-1): 0 always inside, rounds outward to 5,
    pos() clamps to [0, 100], the GMP-implied conversion is display-layer.
"""
from __future__ import annotations

import html
from pathlib import Path

import pytest

import ui.forecast_block as fb
from agent.gmp_schema import GmpQuote, GmpRecord
from pipelines.forecast import load_forecast
from ui.copy import (
    FORECAST_EMPTY_ABSTAIN,
    FORECAST_EMPTY_NOT_COVERED,
    FORECAST_ERROR_STATE,
    FORECAST_GATE_FAIL_HEADING,
    FORECAST_NO_GMP_NOTE,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# A synthetic GMP record (median premium = ₹47) + an issue price so the display-
# layer conversion yields a real implied return (47 / 390 * 100 ≈ 12.05%).
_GMP = GmpRecord(
    drhp_id="swiggy_2024_11",
    computed_at="2026-07-15T00:00:00Z",
    as_of="2024-11-10",
    quotes=[
        GmpQuote(source="aggregator_a", value=40.0, as_of="2024-11-10"),
        GmpQuote(source="aggregator_b", value=54.0, as_of="2024-11-10"),
    ],
)
_ISSUE_PRICE = 390.0


# --------------------------------------------------------------------------- #
# Capture harness — a fake `st` recording every render call.
# --------------------------------------------------------------------------- #


class _FakeContainer:
    def __init__(self, cap: "_CaptureSt", kwargs: dict) -> None:
        self._cap = cap
        self._kwargs = kwargs

    def __enter__(self) -> "_FakeContainer":
        self._cap.containers.append(self._kwargs)
        return self

    def __exit__(self, *exc) -> bool:
        return False


class _CaptureSt:
    def __init__(self) -> None:
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.containers: list[dict] = []
        self.expanders: list[tuple] = []

    def container(self, *args, **kwargs) -> _FakeContainer:
        return _FakeContainer(self, kwargs)

    def markdown(self, body: str, **kwargs) -> None:
        self.markdowns.append(body)

    def caption(self, body: str, **kwargs) -> None:
        self.captions.append(body)

    def expander(self, *args, **kwargs) -> _FakeContainer:
        self.expanders.append((args, kwargs))
        return _FakeContainer(self, kwargs)

    @property
    def joined(self) -> str:
        return "\n".join(self.markdowns + self.captions)

    def plot_markdowns(self) -> list[str]:
        return [m for m in self.markdowns if "drhp-forecast-plot" in m]


@pytest.fixture()
def cap(monkeypatch) -> _CaptureSt:
    capture = _CaptureSt()
    monkeypatch.setattr(fb, "st", capture)
    return capture


# --------------------------------------------------------------------------- #
# Render states
# --------------------------------------------------------------------------- #


def test_full_render_band_gmp_marker_gap_and_metrics(cap: _CaptureSt) -> None:
    """Covered + GMP + issue price → band, GMP marker, labeled gap, always-visible
    metrics strip, and the model-card link — the full headline render."""
    record = load_forecast("swiggy_2024_11")
    fb.render_forecast_block(record, _GMP, _ISSUE_PRICE)

    body = cap.joined
    # ONE self-contained plot markdown (no split div), carrying the amber band.
    assert len(cap.plot_markdowns()) == 1
    assert "drhp-forecast-band" in body
    # The GMP marker (hollow diamond) + the labeled gap line are present.
    assert "drhp-forecast-gmp" in body
    assert "above the GMP-free model median" in body or "below the GMP-free" in body
    assert FORECAST_NO_GMP_NOTE not in body
    # The always-visible honesty strip — coverage / MAE / RMSE, NOT collapsed.
    assert "drhp-forecast-tested" in body
    assert "78.3%" in body  # empirical coverage shown honestly (≠ 80%, P17)
    assert "drhp-forecast-rmse" in body
    assert "2016" in body and "2025" in body
    assert cap.expanders == []  # metrics never behind an expander (L5-3)
    # Model-card link → /methodology.
    assert 'href="/methodology"' in body
    # The card container carries the unique keyed chrome.
    assert {"border": True, "key": "drhpcard-forecast"} in cap.containers


def test_full_render_median_is_a_tick_not_a_display_headline(cap: _CaptureSt) -> None:
    """The median is a faint tick + Small annotation only — never Display-size,
    never a point-estimate headline (P21, L5-1)."""
    record = load_forecast("swiggy_2024_11")
    fb.render_forecast_block(record, _GMP, _ISSUE_PRICE)
    body = cap.joined
    assert "drhp-forecast-median" in body
    assert "Model median 6.1%" in body
    # No Display-size hero number anywhere in the section.
    assert "drhp-hero-display" not in body


def test_gmp_implied_conversion_is_display_layer(cap: _CaptureSt) -> None:
    """The GMP-implied return printed in the gap line is gmp_premium/issue_price*100
    computed in the display layer (median premium 47 / 390 * 100 ≈ 12.1%)."""
    record = load_forecast("swiggy_2024_11")
    fb.render_forecast_block(record, _GMP, _ISSUE_PRICE)
    body = cap.joined
    # 47 / 390 * 100 = 12.05 → one-decimal 12.1; delta from median 6.1 ≈ 5.9 pts.
    assert "implies about 12.1%" in body
    assert "above the GMP-free model median" in body


def test_covered_no_gmp_omits_marker_shows_honest_note(cap: _CaptureSt) -> None:
    """Covered + no GMP → band + median + metrics render; GMP marker + gap line
    omitted; honest no-gap note shown; never a fabricated GMP."""
    record = load_forecast("swiggy_2024_11")
    fb.render_forecast_block(record, None, _ISSUE_PRICE)
    body = cap.joined
    assert len(cap.plot_markdowns()) == 1
    assert "drhp-forecast-band" in body  # band still renders
    assert "drhp-forecast-gmp" not in body  # marker omitted
    assert FORECAST_NO_GMP_NOTE in body  # honest no-gap note
    assert "drhp-forecast-tested" in body  # metrics unchanged


def test_covered_gmp_present_but_no_issue_price_omits_marker(cap: _CaptureSt) -> None:
    """When the issue price is unavailable the marker + gap line are omitted (the
    band still renders) with the honest no-gap note — the conversion needs it."""
    record = load_forecast("swiggy_2024_11")
    fb.render_forecast_block(record, _GMP, None)
    body = cap.joined
    assert "drhp-forecast-band" in body
    assert "drhp-forecast-gmp" not in body
    assert FORECAST_NO_GMP_NOTE in body


def test_abstain_renders_honest_note_no_band(cap: _CaptureSt) -> None:
    """The hyundai abstain record → honest .drhp-not-disclosed note, NO band, NO
    fabricated interval or metrics strip."""
    record = load_forecast("hyundai_2024_10")
    assert record.is_abstain is True
    fb.render_forecast_block(record, _GMP, _ISSUE_PRICE)
    body = cap.joined
    assert html.escape(FORECAST_EMPTY_ABSTAIN) in body
    assert "drhp-forecast-band" not in body
    assert cap.plot_markdowns() == []
    assert "drhp-forecast-tested" not in body


def test_not_covered_renders_honest_note_no_band(cap: _CaptureSt) -> None:
    """render_forecast_not_covered → heading + honest not-covered note, NO band."""
    fb.render_forecast_not_covered()
    body = cap.joined
    assert html.escape(FORECAST_EMPTY_NOT_COVERED) in body
    assert "drhp-forecast-band" not in body
    assert {"border": True, "key": "drhpcard-forecast-empty"} in cap.containers


# --------------------------------------------------------------------------- #
# P9-fail honesty banner (Option A) — the shipped model failed its release gate;
# the covered band still renders but is reframed as calibration transparency.
# --------------------------------------------------------------------------- #


def test_gate_banner_html_amber_when_failed() -> None:
    """A failed P9 gate → an amber honest-caution banner naming the fail + a model-
    card link, WITHOUT role=alert (static framing, not an urgent live alert)."""
    out = fb._gate_banner_html(True)
    assert "drhp-refusal" in out  # the project's amber honest-caution treatment
    assert "drhp-forecast-gatefail" in out  # dedicated hook class
    assert FORECAST_GATE_FAIL_HEADING in out
    assert 'href="/methodology"' in out  # links to the full model card
    assert 'role="alert"' not in out


def test_gate_banner_html_empty_when_passed() -> None:
    """A passing gate → no banner (the band stands on its own)."""
    assert fb._gate_banner_html(False) == ""


def test_gate_failed_reads_committed_card_verdict(tmp_path, monkeypatch) -> None:
    """_gate_failed reads the committed card_data.json (cache-only, no model import).
    A missing/unreadable card never ASSERTS a fail we cannot read."""
    card = tmp_path / "card_data.json"
    card.write_text('{"gate_passed": false}', encoding="utf-8")
    monkeypatch.setattr(fb, "_CARD_DATA_PATH", card)
    assert fb._gate_failed() is True

    card.write_text('{"gate_passed": true}', encoding="utf-8")
    assert fb._gate_failed() is False

    monkeypatch.setattr(fb, "_CARD_DATA_PATH", tmp_path / "absent.json")
    assert fb._gate_failed() is False


def test_covered_render_leads_with_gatefail_banner(cap: _CaptureSt, monkeypatch) -> None:
    """Option A: when the model failed its gate the covered block LEADS with the
    honesty banner, and the calibrated band STILL renders below it."""
    monkeypatch.setattr(fb, "_gate_failed", lambda: True)
    record = load_forecast("swiggy_2024_11")
    fb.render_forecast_block(record, None, _ISSUE_PRICE)

    body = cap.joined
    assert "drhp-forecast-gatefail" in body  # honesty banner present
    assert "drhp-forecast-band" in body  # band STILL renders (Option A)
    # the banner precedes the plot in render order
    idx_banner = next(
        i for i, m in enumerate(cap.markdowns) if "drhp-forecast-gatefail" in m
    )
    idx_plot = next(
        i for i, m in enumerate(cap.markdowns) if "drhp-forecast-plot" in m
    )
    assert idx_banner < idx_plot


def test_covered_render_no_banner_when_gate_passes(cap: _CaptureSt, monkeypatch) -> None:
    monkeypatch.setattr(fb, "_gate_failed", lambda: False)
    record = load_forecast("swiggy_2024_11")
    fb.render_forecast_block(record, None, _ISSUE_PRICE)
    assert "drhp-forecast-gatefail" not in cap.joined


def test_error_renders_amber_refusal_not_red(cap: _CaptureSt) -> None:
    """render_forecast_error → the inherited amber .drhp-refusal banner (NOT red)."""
    fb.render_forecast_error()
    body = cap.joined
    assert "drhp-refusal" in body
    assert 'role="alert"' in body
    assert html.escape(FORECAST_ERROR_STATE) in body


def test_record_sourced_string_is_html_escaped(cap: _CaptureSt) -> None:
    """A record-sourced string (backtest_window) is html.escape'd before it reaches
    the unsafe_allow_html strip (T-05-07-XSS)."""
    record = load_forecast("swiggy_2024_11")
    record.metrics.backtest_window = '2016<script>"2025'
    fb.render_forecast_block(record, None, None)
    body = cap.joined
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


# --------------------------------------------------------------------------- #
# D-1 axis-domain + marker-position math
# --------------------------------------------------------------------------- #


def test_domain_includes_zero_and_rounds_outward_to_5() -> None:
    """_domain always contains 0 and rounds both bounds outward to a multiple of 5."""
    lo, hi = fb._domain([0.0, -4.2, 21.7, 6.1])
    assert lo <= 0.0 <= hi
    assert lo % 5 == 0 and hi % 5 == 0
    assert lo == -10.0 and hi == 25.0


def test_domain_padding_floor_of_2_points() -> None:
    """A very tight interval still gets a >= 2.0-point pad before outward rounding."""
    lo, hi = fb._domain([0.0, 0.5, 1.0, 0.75])
    # raw span 1.0 → 0.08*1.0 = 0.08 < 2.0 → pad = 2.0; floor_to_5(-2)= -5, ceil_to_5(3)=5
    assert lo == -5.0 and hi == 5.0


def test_pos_clamps_to_0_100_and_maps_domain_ends() -> None:
    """pos maps domain_lo→0, domain_hi→100 and clamps out-of-range values."""
    lo, hi = -10.0, 25.0
    assert fb.pos(lo, lo, hi) == 0.0
    assert fb.pos(hi, lo, hi) == 100.0
    assert fb.pos(-999.0, lo, hi) == 0.0
    assert fb.pos(999.0, lo, hi) == 100.0
    assert 0.0 < fb.pos(0.0, lo, hi) < 100.0


def test_gmp_implied_return_pct_is_display_conversion() -> None:
    """gmp_premium / issue_price * 100, with None when the issue price is absent."""
    assert fb._gmp_implied_return_pct(47.0, 390.0) == pytest.approx(12.0512, abs=1e-3)
    assert fb._gmp_implied_return_pct(47.0, None) is None
    assert fb._gmp_implied_return_pct(47.0, 0) is None


def test_band_has_4px_minimum_visual_width_floor() -> None:
    """The interval band carries a >= 4px min visual width so a genuinely tiny
    interval is still visible (the caption still states the true span, D-1)."""
    css = (REPO_ROOT / "app" / "static" / "drhplens.css").read_text(encoding="utf-8")
    band_rule = css.split(".drhp-forecast-band")[1].split("}")[0]
    assert "min-width: 4px" in band_rule
