"""
annotator.py — Stance annotation by a third LLM judge.

The annotator reads an agent's utterances from a completed exchange and returns
a LikertStance. It is entirely separate from the agent LLMs — it sees the
exchange as a reader, not a participant.

Bias prevention: The annotator prompt instructs the LLM to report the stance
the agent expressed, not the annotator's own view. The full Likert scale
definition is included so the model uses a consistent frame every time.

Retry logic: up to MAX_RETRIES attempts on AnnotationError (unparseable output).
After all retries fail, returns the agent's previous stance as a safe fallback
(logged as a warning — not a crash).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import LikertStance, SimulationConfig
    from exchange import ExchangeTurn
    from personas import AgentPersona

from config import AnnotationError, parse_likert
from llm import llm_call
from prompts import (
    LIKERT_SCALE_DEFINITION,
    AnnotatorSystemPrompt,
    AnnotatorUserPrompt,
)

log = logging.getLogger(__name__)

MAX_RETRIES = 3
_system_prompt = AnnotatorSystemPrompt()
_user_prompt   = AnnotatorUserPrompt()


async def annotate(
    agent: "AgentPersona",
    exchange_log: list["ExchangeTurn"],
    previous_stance: "LikertStance",
    config: "SimulationConfig",
) -> "LikertStance":
    """
    Annotate the stance of `agent` based on their utterances in `exchange_log`.

    Parameters
    ----------
    agent           : the agent being annotated
    exchange_log    : full list of turns from the exchange
    previous_stance : the agent's stance before this exchange (used as fallback)
    config          : simulation config

    Returns
    -------
    LikertStance — the annotated stance after this exchange.
    """
    # Collect only this agent's utterances
    agent_utterances = [
        t.utterance
        for t in exchange_log
        if t.speaker_id == agent.agent_id
    ]

    if not agent_utterances:
        # Agent didn't speak (shouldn't happen, but handle gracefully)
        return previous_stance

    utterances_text = "\n".join(
        f"[Turn {i + 1}] {utt}" for i, utt in enumerate(agent_utterances)
    )

    system = _system_prompt.render(
        topic=config.topic,
        scale_definition=LIKERT_SCALE_DEFINITION,
    )
    user = _user_prompt.render(
        name=agent.name,
        topic=config.topic,
        utterances=utterances_text,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = await llm_call(system, user, config)
            return parse_likert(raw)
        except AnnotationError as exc:
            if attempt < MAX_RETRIES:
                log.warning(
                    "Annotation attempt %d/%d failed for %s: %s. Retrying.",
                    attempt, MAX_RETRIES, agent.name, exc,
                )
            else:
                log.warning(
                    "All %d annotation attempts failed for %s. "
                    "Keeping previous stance: %s.",
                    MAX_RETRIES, agent.name, previous_stance.label,
                )
                return previous_stance
