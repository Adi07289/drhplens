"""Offline runner test for scripts.run_eval.run_rag_eval (06.1-04, EVAL-01).

Drives the RAG eval runner FULLY OFFLINE — no live Qdrant / Gemini / Langfuse — by
injecting a stub agent (``invoke_fn``) and monkeypatching the DeepEval judge. It pins the
committed contract the inline UI surface (06.1-06) and the release gate (06.1-05) read:

  1. the emitted ``eval_summary.json`` validates against the pinned ``EvalSummary`` schema;
  2. ``judge_model`` is a named, non-empty judge (honesty-invariant provenance);
  3. ``per_ipo`` carries ONLY the Swiggy key (never a fabricated per-IPO figure — T-6.1-12);
  4. the dated ``.md`` carries the P10 recall-saturation floor caveat + the gold-set follow-up;
  5. recall was computed over ``retrieved_chunks`` (the 50 candidates), NOT the 5 reranked
     chunks — proven by a stub whose overlapping candidate sits at index 7 (inside top-10,
     outside top-5), so recall@5=0.0 while recall@10=1.0 (impossible off a 5-item reranked list).
"""
from __future__ import annotations

import json
import types
from datetime import date
from pathlib import Path

from agent.policies import DRHP_ID_DEFAULT
from eval.metrics import EvalSummary

# The gold question's expected source: a specific page span the stub is crafted around.
_EXPECTED = [{"section": "Financials", "page_start": 100, "page_end": 110}]


def _chunk(page_start: int, page_end: int, text: str = "boilerplate") -> dict:
    """A retrieval-candidate dict shaped like storage.vector.search() output."""
    return {
        "chunk_id": f"c{page_start}-{page_end}",
        "score": 0.5,
        "payload": {"page_start": page_start, "page_end": page_end, "chunk_text": text},
    }


def _stub_final_state() -> dict:
    """A final_state whose OVERLAPPING candidate sits at index 7 of retrieved_chunks.

    - retrieved_chunks (50 candidates): all page 1-2 EXCEPT index 7, which overlaps the
      expected span (100-110). Index 7 is inside top-10 but outside top-5.
    - reranked_top_k (5 chunks): all page 1-2 — NONE overlap the expected span.

    Consequences (proving the metric source):
      recall@5  over retrieved[:5]  -> 0.0 (overlap at index 7, not in top-5)
      recall@10 over retrieved[:10] -> 1.0 (overlap at index 7, in top-10)
      citation  over reranked (5)   -> 0.0 (no reranked chunk overlaps)
    If recall were (wrongly) computed over the 5 reranked chunks, recall@10 would be 0.0.
    """
    retrieved = [_chunk(1, 2) for _ in range(50)]
    retrieved[7] = _chunk(100, 110, text="FY2024 revenue Rs 11,247 crore.")
    reranked = [_chunk(1, 2) for _ in range(5)]
    grounded_answer = types.SimpleNamespace(answer_prose="Revenue was Rs 11,247 crore.")
    return {
        "question": "stub",
        "retrieved_chunks": retrieved,
        "reranked_top_k": reranked,
        "grounded_answer": grounded_answer,
        "refusal": None,
    }


def _write_gold(tmp_path: Path) -> Path:
    """A one-question grounded gold set (plus a refusal-eligible row that must be excluded)."""
    gold = tmp_path / "gold.jsonl"
    rows = [
        {
            "qid": "stub-001",
            "category": "numeric",
            "question": "What was FY2024 revenue?",
            "expected_answer_contains": ["11,247"],
            "expected_sources": _EXPECTED,
            "is_refusal_expected": False,
        },
        {
            "qid": "stub-002",
            "category": "refusal-eligible",
            "question": "What is today's market cap?",
            "expected_answer_contains": [],
            "expected_sources": [],
            "is_refusal_expected": True,
        },
    ]
    gold.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return gold


def test_run_rag_eval_offline_contract(tmp_path, monkeypatch) -> None:
    """run_rag_eval emits a schema-valid JSON + a P10 .md fully offline (injected agent + judge)."""
    import scripts.run_eval as run_eval

    # Offline guarantees: no Langfuse network (both is_enabled implementations read these).
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    # Stub the DeepEval judge to a fixed measured value (module-level name -> monkeypatchable).
    def _fake_judge(question: str, answer: str, contexts: list[str]) -> tuple[float, str]:
        # contexts must be the byte-identical top-5 reranked chunk text the agent consumed (P18).
        assert isinstance(contexts, list)
        return 0.9, "stub judge reason: all claims supported"

    monkeypatch.setattr(run_eval, "faithfulness_deepeval", _fake_judge)

    # Stub the agent — matches invoke_with_tracing(initial_state, question) -> final_state.
    def _fake_invoke(initial_state: dict, question: str) -> dict:
        return _stub_final_state()

    gold = _write_gold(tmp_path)
    json_path = run_eval.run_rag_eval(
        gold_set_path=str(gold),
        output_dir=str(tmp_path),
        with_faithfulness=True,
        invoke_fn=_fake_invoke,
    )

    # (1) the emitted JSON validates against the pinned UI/gate contract.
    assert json_path == tmp_path / "eval_summary.json"
    summary = EvalSummary.model_validate_json(json_path.read_text(encoding="utf-8"))

    # (2) named judge (honesty-invariant provenance).
    assert summary.judge_model

    # (3) per_ipo carries ONLY Swiggy — never a fabricated per-IPO figure.
    assert list(summary.per_ipo.keys()) == [DRHP_ID_DEFAULT]

    # (5) recall came from retrieved_chunks (50), not reranked (5): recall@5=0.0 while
    #     recall@10=1.0 is only possible off a >5 candidate list ordered by the stub.
    assert summary.aggregate.recall_at_5 == 0.0
    assert summary.aggregate.recall_at_10 == 1.0
    assert summary.aggregate.recall_at_30 == 1.0
    # citation is over the (non-overlapping) reranked window -> 0.0, confirming the split.
    assert summary.aggregate.citation_accuracy == 0.0
    # the monkeypatched judge value flowed into the aggregate.
    assert summary.aggregate.faithfulness_deepeval == 0.9

    # (4) the .md carries the P10 recall-saturation floor caveat + the gold-set follow-up.
    md = (tmp_path / f"{date.today()}-rag-eval.md").read_text(encoding="utf-8")
    lower = md.lower()
    assert "regression floor" in lower
    assert "44.5" in md  # the coarse-span smoking gun (spike 003)
    assert "evaluation theater" in lower
    assert "gold-set follow-up" in lower
    assert "interpretation (p10)" in lower
    # judge reason strings are committed to the human report.
    assert "stub judge reason" in md


def test_run_rag_eval_default_is_not_measured_sentinel(tmp_path, monkeypatch) -> None:
    """Without --with-faithfulness, the committed faithfulness is the -1 'not measured'
    sentinel (P10 honesty guard) while recall/citation stay REAL — all offline."""
    import scripts.run_eval as run_eval

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    def _fake_invoke(initial_state: dict, question: str) -> dict:
        return _stub_final_state()

    gold = _write_gold(tmp_path)
    json_path = run_eval.run_rag_eval(
        gold_set_path=str(gold),
        output_dir=str(tmp_path),
        with_faithfulness=False,
        invoke_fn=_fake_invoke,
    )

    summary = EvalSummary.model_validate_json(json_path.read_text(encoding="utf-8"))
    assert summary.aggregate.faithfulness_deepeval == -1.0  # not measured, never a real 0.0
    assert summary.aggregate.recall_at_10 == 1.0  # deterministic metric still REAL
    assert summary.corpus.n_questions == 2  # full gold-set size (grounded + refusal-eligible)
