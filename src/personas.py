"""
personas.py — Loads agent personas from the active topic module.

The topic is set via the TOPIC env var (e.g. TOPIC=immigration).
This file contains no persona data itself — all personas live in topics/.

To add a new topic (e.g. "climate"):
  1. Create topics/climate.py following the same schema as topics/immigration.py
  2. Set TOPIC=climate in .env
  3. Run — nothing else needs to change

AgentPersona is defined here because it is a pure data type used across
multiple modules (exchange.py, annotator.py, simulation.py).
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import SimulationConfig

from config import LikertStance, PoliticalLeaning


# ── AgentPersona data type ────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPersona:
    agent_id:            str
    name:                str
    leaning:             PoliticalLeaning
    age:                 int
    occupation:          str
    persona_description: str
    initial_stance:      LikertStance


# ── Topic loader ──────────────────────────────────────────────────────────────

def _load_topic(topic_name: str) -> tuple[str, list[AgentPersona]]:
    """
    Import topics/{topic_name}.py and return (topic_label, personas_list).

    The topic module must define:
      TOPIC_LABEL : str         — full label used in prompts
      PERSONAS    : list[dict]  — one dict per agent (keys match AgentPersona fields)
    """
    # Normalise: "immigration policy" → "immigration"
    slug = topic_name.strip().lower().split()[0]

    # Topics live one directory up from src/
    topics_dir = Path(__file__).parent.parent / "topics"
    topic_file = topics_dir / f"{slug}.py"

    if not topic_file.exists():
        available = [f.stem for f in topics_dir.glob("*.py") if f.stem != "__init__"]
        raise FileNotFoundError(
            f"No topic file found for '{slug}' at {topic_file}.\n"
            f"Available topics: {available}\n"
            f"To add a new topic, create topics/{slug}.py following the schema in topics/immigration.py"
        )

    # Dynamic import
    spec   = importlib.util.spec_from_file_location(f"topics.{slug}", topic_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    topic_label = module.TOPIC_LABEL
    personas = [
        AgentPersona(
            agent_id            = p["agent_id"],
            name                = p["name"],
            leaning             = p["leaning"],
            age                 = p["age"],
            occupation          = p["occupation"],
            persona_description = p["persona_description"],
            initial_stance      = p["initial_stance"],
        )
        for p in module.PERSONAS
    ]
    return topic_label, personas


# ── Public API ─────────────────────────────────────────────────────────────────

def create_personas(config: "SimulationConfig") -> list[AgentPersona]:
    """
    Load and return agent personas for the topic specified in config.

    Only the first config.n_agents personas are returned (in definition order).
    Raises ValueError if n_agents exceeds the number defined for that topic.
    """
    _, personas = _load_topic(config.topic)

    if config.n_agents > len(personas):
        raise ValueError(
            f"n_agents={config.n_agents} exceeds personas available for topic "
            f"'{config.topic}' ({len(personas)}). "
            f"Add more agents to topics/{config.topic.split()[0]}.py or reduce n_agents."
        )
    return personas[: config.n_agents]


def get_topic_label(topic_name: str) -> str:
    """Return the full topic label string for use in prompts and logging."""
    label, _ = _load_topic(topic_name)
    return label
