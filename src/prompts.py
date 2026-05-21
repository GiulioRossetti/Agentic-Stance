"""
prompts.py — All prompt templates as typed, frozen dataclasses.

Every prompt is a class with:
- required_keys: tuple of keyword argument names that .render() accepts
- render(**kwargs): returns the filled string

Annotator prompt design note: The annotator is explicitly instructed to report
the stance the agent expressed, not the annotator's own view on the topic.
This prevents annotator bias from contaminating the stance trajectory data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


# ── Base class ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BasePrompt:
    required_keys: ClassVar[tuple[str, ...]]

    def render(self, **kwargs: str) -> str:
        raise NotImplementedError


# ── 1. Agent system prompt ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentSystemPrompt(BasePrompt):
    """
    Sets up the agent's identity. The agent knows who they are, their leaning,
    the topic, and their current stance. They are NOT told to agree or disagree —
    they reason freely based on their persona.
    """
    required_keys: ClassVar[tuple[str, ...]] = (
        "name", "age", "occupation", "leaning", "persona_description",
        "topic", "current_stance",
    )

    def render(self, *, name: str, age: str, occupation: str, leaning: str, persona_description: str, topic: str, current_stance: str) -> str:
        return (
            f"You are {name}, a {age}-year-old {occupation} with a {leaning.replace('_', ' ')} "
            f"political outlook.\n\n"
            f"{persona_description}\n\n"
            f"You are taking part in a discussion about {topic}. "
            f"Your current position on this topic is: {current_stance}.\n\n"
            "Speak naturally as yourself. Engage with what the other person says. "
            "You may change your mind if you find their argument genuinely convincing, "
            "or you may push back if you disagree. Do not simply agree to be agreeable."
        )


# ── 2. Agent user prompt ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentUserPrompt(BasePrompt):
    """
    Provides the agent with their memory context and the current exchange history,
    then asks them to respond. KG context is injected here — empty string if no memory.
    """
    required_keys: ClassVar[tuple[str, ...]] = (
        "kg_context", "exchange_history",
    )

    def render(self, *, kg_context: str, exchange_history: str) -> str:
        parts: list[str] = []

        if kg_context.strip():
            parts.append(
                "Here is what you remember from previous conversations on this topic:\n"
                f"{kg_context}\n"
            )

        if exchange_history.strip():
            parts.append(
                "The conversation so far:\n"
                f"{exchange_history}\n"
            )

        parts.append("Now respond to the other person. Keep your reply to 2–4 sentences.")
        return "\n".join(parts)


# ── 3. Annotator system prompt ─────────────────────────────────────────────────

@dataclass(frozen=True)
class AnnotatorSystemPrompt(BasePrompt):
    """
    The annotator is a neutral stance-reader. It must report what the agent expressed,
    not the annotator's own opinion on the topic. This is enforced explicitly in the prompt.
    """
    required_keys: ClassVar[tuple[str, ...]] = ("topic", "scale_definition")

    def render(self, *, topic: str, scale_definition: str) -> str:
        return (
            f"You are a neutral stance annotator. Your task is to read an agent's statements "
            f"from a discussion about {topic} and identify the stance they expressed.\n\n"
            "IMPORTANT: You must report the stance the agent expressed, regardless of whether "
            "you agree with it or consider it reasonable. Do not let your own views on the topic "
            "influence the label you assign.\n\n"
            f"Use the following scale:\n{scale_definition}\n\n"
            "Output exactly one label from the scale above, on its own line, with no extra text."
        )


# ── 4. Annotator user prompt ───────────────────────────────────────────────────

@dataclass(frozen=True)
class AnnotatorUserPrompt(BasePrompt):
    """Provides the agent's utterances and asks for one Likert label."""
    required_keys: ClassVar[tuple[str, ...]] = ("name", "topic", "utterances")

    def render(self, *, name: str, topic: str, utterances: str) -> str:
        return (
            f"Agent: {name}\n"
            f"Topic: {topic}\n\n"
            f"Statements made by {name} during this exchange:\n"
            f"{utterances}\n\n"
            f"What is {name}'s stance on {topic}? "
            "Output exactly one label from the scale."
        )


# ── 5. Triplet extractor system prompt ────────────────────────────────────────

@dataclass(frozen=True)
class TripletSystemPrompt(BasePrompt):
    """Instructs the LLM to extract subject-predicate-object facts from text."""
    required_keys: ClassVar[tuple[str, ...]] = ("dimension",)

    def render(self, *, dimension: str) -> str:
        dimension_guidance = {
            "general": "facts about the topic, policies, or events mentioned",
            "tom": "what the speaker believes about the other person's views or stance",
            "beliefs": "the speaker's own stated positions, values, or opinions",
        }.get(dimension, "relevant facts")

        return (
            "You extract knowledge graph triplets from text. "
            f"Focus on: {dimension_guidance}.\n\n"
            "For each fact, output one line in this exact format:\n"
            "  subject | predicate | object\n\n"
            "Rules:\n"
            "- Extract only what is clearly stated, not inferred\n"
            "- Keep each part short (3–8 words)\n"
            "- Output 0–5 triplets\n"
            "- If there is nothing to extract, output: NONE"
        )


# ── 6. Triplet extractor user prompt ──────────────────────────────────────────

@dataclass(frozen=True)
class TripletUserPrompt(BasePrompt):
    """Provides the text to extract triplets from."""
    required_keys: ClassVar[tuple[str, ...]] = ("text",)

    def render(self, *, text: str) -> str:
        return f"Extract triplets from this statement:\n\n{text}"


# ── Registry ───────────────────────────────────────────────────────────────────

ALL_PROMPTS: tuple[type[BasePrompt], ...] = (
    AgentSystemPrompt,
    AgentUserPrompt,
    AnnotatorSystemPrompt,
    AnnotatorUserPrompt,
    TripletSystemPrompt,
    TripletUserPrompt,
)

# ── Constant: Likert scale definition (injected into annotator prompt) ─────────

LIKERT_SCALE_DEFINITION = (
    "  Strongly Against  — the agent clearly and firmly opposes the proposition\n"
    "  Against           — the agent tends to oppose the proposition\n"
    "  Neutral           — the agent is undecided, balanced, or non-committal\n"
    "  In Favor          — the agent tends to support the proposition\n"
    "  Strongly In Favor — the agent clearly and firmly supports the proposition"
)
