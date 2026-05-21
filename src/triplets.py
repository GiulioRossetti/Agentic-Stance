"""
triplets.py — Extract knowledge graph triplets from text using an LLM.

Each triplet is (subject, predicate, object, dimension) where dimension is
one of: "general" | "tom" | "beliefs".

  general  — facts about the topic, events, or policies
  tom      — what the speaker believes about the other person's views (Theory of Mind)
  beliefs  — the speaker's own stated positions, values, or opinions

The extraction LLM is called once per utterance per absorb() call.
If parsing fails (model produces non-standard output), returns an empty list —
the simulation never crashes because triplet extraction failed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import SimulationConfig

from llm import llm_call
from prompts import TripletSystemPrompt, TripletUserPrompt

log = logging.getLogger(__name__)

_system_prompt = TripletSystemPrompt()
_user_prompt   = TripletUserPrompt()


@dataclass(frozen=True)
class Triplet:
    subject:   str
    predicate: str
    object:    str
    dimension: str  


async def extract_triplets(
    text: str,
    dimension: str,
    config: "SimulationConfig",
) -> list[Triplet]:
    """
    Extract KG triplets from `text` for the given KG `dimension`.

    Returns an empty list on any parsing failure (never raises).
    """
    system = _system_prompt.render(dimension=dimension)
    user   = _user_prompt.render(text=text)

    try:
        raw = await llm_call(system, user, config)
    except Exception as exc:
        log.warning("Triplet extraction LLM call failed: %s. Skipping.", exc)
        return []

    return _parse_triplets(raw, dimension)


def _parse_triplets(raw: str, dimension: str) -> list[Triplet]:
    """
    Parse pipe-separated triplet lines from LLM output.

    Expected format (one per line):
        subject | predicate | object

    Lines that don't match are silently skipped.
    "NONE" response → empty list.
    """
    if raw.strip().upper() == "NONE":
        return []

    triplets: list[Triplet] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.upper() == "NONE":
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            log.debug("Skipping malformed triplet line: %r", line)
            continue
        subject, predicate, obj = parts
        if subject and predicate and obj:
            triplets.append(Triplet(subject, predicate, obj, dimension))

    return triplets
