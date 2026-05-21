"""
llm.py — Single async function for all LLM provider calls.

All providers return a plain string. All failures raise LLMError.
No retry logic here — callers decide whether to retry and how many times.

Supported providers:
ollama     — local Ollama (primary; free, reproducible, no rate limits)
anthropic  — Claude models via Anthropic API
openai     — GPT models via OpenAI API
groq       — Llama models via Groq API (fast, generous free tier)
gemini     — Gemini models via Google Generative AI API
Add a new provider by adding one branch to llm_call() only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import SimulationConfig

from config import LLMError


async def llm_call(system: str, user: str, config: "SimulationConfig") -> str:
    """
    Call the configured LLM provider with a system prompt and a user message.
    Returns the model's text response as a plain string.
    Raises LLMError on any failure.
    """
    provider = config.llm_provider
    model = config.llm_model

    if provider == "ollama":
        return await _call_ollama(system, user, model)
    elif provider == "anthropic":
        return await _call_anthropic(system, user, model)
    elif provider == "openai":
        return await _call_openai(system, user, model)
    elif provider == "groq":
        return await _call_groq(system, user, model)
    else:
        raise LLMError(f"Unknown provider: {provider!r}")


async def _call_ollama(system: str, user: str, model: str) -> str:
    try:
        import ollama
        client = ollama.AsyncClient()
        response = await client.chat(
            model=model,
            messages=[
                {"role": "system",    "content": system},
                {"role": "user",      "content": user},
            ],
        )
        return response.message.content.strip()
    except ImportError:
        raise LLMError("ollama package not installed. Run: pip install ollama")
    except Exception as exc:
        raise LLMError(f"Ollama call failed: {exc}") from exc


async def _call_anthropic(system: str, user: str, model: str) -> str:
    try:
        import anthropic
        import os
        client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = await client.messages.create(
            model=model,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text.strip()
    except ImportError:
        raise LLMError("anthropic package not installed. Run: pip install anthropic")
    except KeyError:
        raise LLMError("ANTHROPIC_API_KEY not set in environment")
    except Exception as exc:
        raise LLMError(f"Anthropic call failed: {exc}") from exc


async def _call_openai(system: str, user: str, model: str) -> str:
    try:
        import openai
        import os
        client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise LLMError("openai package not installed. Run: pip install openai")
    except KeyError:
        raise LLMError("OPENAI_API_KEY not set in environment")
    except Exception as exc:
        raise LLMError(f"OpenAI call failed: {exc}") from exc


async def _call_groq(system: str, user: str, model: str) -> str:
    try:
        import groq
        import os
        client = groq.AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise LLMError("groq package not installed. Run: pip install groq")
    except KeyError:
        raise LLMError("GROQ_API_KEY not set in environment")
    except Exception as exc:
        raise LLMError(f"Groq call failed: {exc}") from exc

async def _call_gemini(system: str, user: str, model: str) -> str:
    try:
        from google import genai
        import os
        client = genai.GenerativeAI(api_key=os.environ["GOOGLE_API_KEY"])
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise LLMError("google-genai package not installed. Run: pip install google-genai")
    except KeyError:
        raise LLMError("GOOGLE_API_KEY not set in environment")
    except Exception as exc:
        raise LLMError(f"Gemini call failed: {exc}") from exc