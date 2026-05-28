"""
agent/demo.py — DRHPLens Walking Skeleton CLI.

Usage:
    python -m agent.demo "What is Swiggy's issue size?"
    python -m agent.demo "What does Swiggy say about Mars colonization?"
    python -m agent.demo "Should I subscribe to Swiggy?"

WITHOUT keys (GEMINI_API_KEY / QDRANT_URL not set):
    Prints a clear error explaining what is missing, then exits with code 0.
    (Does not pretend it worked; does not crash with a traceback.)

WITH keys:
    Runs the full agent end-to-end on Swiggy DRHP.
    Returns a GroundedAnswer (with {{claim_id}} placeholders) or a RefusalResponse.

Walking Skeleton assertion: this file exists + imports cleanly + would work
end-to-end with GEMINI_API_KEY + QDRANT_URL set.

Wave 4's app.py calls the same GRAPH.invoke() with the same state shape.
"""
from __future__ import annotations

import sys
import uuid

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text

from agent.graph import GRAPH
from agent.schemas import GroundedAnswer, RefusalResponse

app = typer.Typer(
    help="DRHPLens Walking Skeleton CLI — one cited answer per invocation.",
    add_completion=False,
)

BANNER = (
    "[bold cyan]DRHPLens[/bold cyan] · Phase 1 Walking Skeleton · "
    "[italic]informational only — not advice (D-07)[/italic]"
)


def _check_env() -> list[str]:
    """Return a list of missing environment variables required for live operation."""
    import os

    missing = []
    if not os.environ.get("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")
    # QDRANT_URL defaults to localhost if not set; flag it as a warning but not fatal
    return missing


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about the Swiggy DRHP prospectus."),
) -> None:
    """Invoke the DRHPLens agent and print the cited answer or refusal.

    Exercises all three SKELETON.md branches:
    - Grounded question → GroundedAnswer with {{claim_id}} placeholders
    - Off-topic question → RefusalResponse(reason=low_retrieval_score) with reformulation chips
    - Banned-token question → RefusalResponse(reason=banned_token) after retry budget exhausted
    """
    rprint(Panel(BANNER, expand=False))
    rprint()

    missing_keys = _check_env()
    if missing_keys:
        rprint(
            f"[yellow]WARNING: Missing environment variables: {', '.join(missing_keys)}[/yellow]\n"
            f"[dim]The agent needs these to run end-to-end:\n"
            f"  export GEMINI_API_KEY=<your-gemini-api-key>\n"
            f"  export QDRANT_URL=<your-qdrant-url>  (defaults to http://localhost:6333)\n\n"
            f"With keys set, re-run:\n"
            f"  python -m agent.demo \"{question}\"[/dim]"
        )
        rprint()
        rprint("[dim]Informational only — not advice.[/dim]")
        raise typer.Exit(code=0)

    thread_id = f"demo-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "question": question,
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": False,
        "gate1_max_score": 0.0,
        "sub_questions": [question],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
    }

    try:
        final_state = GRAPH.invoke(initial_state, config=config)
    except Exception as exc:
        rprint(f"[red]Agent error: {exc}[/red]")
        rprint("[dim]Informational only — not advice.[/dim]")
        raise typer.Exit(code=1)

    refusal: RefusalResponse | None = final_state.get("refusal")
    grounded_answer: GroundedAnswer | None = final_state.get("grounded_answer")

    if refusal is not None:
        rprint(f"[bold red]Refusal (reason: {refusal.reason})[/bold red]")
        rprint(f"{refusal.explanation}")
        if refusal.reformulation_suggestions:
            rprint("\n[bold]Suggestions — try asking about:[/bold]")
            for suggestion in refusal.reformulation_suggestions:
                rprint(f"  · {suggestion}")
    elif grounded_answer is not None:
        rprint(f"[bold green]Answer:[/bold green]")
        rprint(grounded_answer.answer_prose)
        rprint()
        if grounded_answer.claims:
            rprint("[bold]Citations:[/bold]")
            for claim in grounded_answer.claims:
                rprint(
                    f"  [{claim.claim_id}] {claim.text} "
                    f"— {claim.section}, page {claim.drhp_page}"
                )
        if grounded_answer.sub_question_unaddressed:
            rprint()
            rprint("[yellow]Note: The DRHP did not address:[/yellow]")
            for uq in grounded_answer.sub_question_unaddressed:
                rprint(f"  · {uq}")
    else:
        rprint("[yellow]No answer produced. Check the agent configuration.[/yellow]")

    rprint()
    rprint("[dim]Informational only — not advice.[/dim]")


if __name__ == "__main__":
    app()
