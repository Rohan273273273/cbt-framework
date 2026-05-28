import json
import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


def reason(prompt: str, context: Dict[str, Any] = None,
           system: str = "You are a professional crypto trading analyst.") -> str:
    """
    Call Ollama for natural language reasoning.
    Returns structured text or falls back to a deterministic summary on timeout/error.
    """
    context = context or {}
    full_prompt = f"{prompt}\n\nContext:\n{json.dumps(context, indent=2, default=str)}"

    try:
        resp = httpx.post(
            f"{settings.ollama_host}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": full_prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 200},
            },
            timeout=settings.ollama_timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except httpx.TimeoutException:
        logger.warning("Ollama timeout — using fallback reasoning")
        return _fallback_reason(context)
    except Exception as e:
        logger.warning(f"Ollama error: {e} — using fallback")
        return _fallback_reason(context)


def _fallback_reason(context: Dict) -> str:
    parts = []
    if "selection" in context and context["selection"]:
        sel = context["selection"]
        parts.append(f"Strategy: {sel.get('strategy')} (confidence={sel.get('confidence', 0):.2f})")
    if "news_sentiment_avg" in context:
        parts.append(f"News sentiment: {context['news_sentiment_avg']:.2f}")
    if "risk_approved" in context:
        parts.append(f"Risk: {'approved' if context['risk_approved'] else 'blocked'}")
    return " | ".join(parts) if parts else "No context available"
