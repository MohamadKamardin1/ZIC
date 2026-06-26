import json
import logging

import requests
from django.conf import settings

from .prompts import SYSTEM_PROMPT, CLARIFICATION_PROMPT

logger = logging.getLogger(__name__)


def _call_deepseek(messages: list, temperature: float = 0.1, max_tokens: int = 2000, timeout: int = 30) -> str:
    api_key = getattr(settings, "DEEPSEEK_API_KEY", None)
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned
    except requests.RequestException as e:
        logger.error(f"DeepSeek API call failed: {e}")
        raise RuntimeError(f"AI service unavailable: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse DeepSeek response: {e}")
        raise RuntimeError(f"AI response parsing failed: {e}")


class DeepSeekService:

    @classmethod
    def analyze_partner_prompt(cls, user_prompt: str) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        content = _call_deepseek(messages)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}, content: {content[:200]}")
            raise RuntimeError(f"AI response parsing failed: {e}")

    @classmethod
    def clarify_partner_data(cls, user_prompt: str, partial_data: dict, missing_fields: list[str]) -> dict:
        prompt = CLARIFICATION_PROMPT.format(
            partial_data=json.dumps(partial_data, indent=2),
            missing_fields=", ".join(missing_fields),
            user_prompt=user_prompt,
        )
        messages = [
            {"role": "system", "content": "You are a helpful assistant that extracts structured partner data."},
            {"role": "user", "content": prompt},
        ]
        content = _call_deepseek(messages, temperature=0.1, max_tokens=2000)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Clarification JSON parse error: {e}, content: {content[:200]}")
            raise RuntimeError(f"AI response parsing failed: {e}")

    @classmethod
    def explain_missing_fields(cls, missing_required: list[str], missing_optional: list[str]) -> str:
        if not missing_required and not missing_optional:
            return ""

        parts = []
        if missing_required:
            parts.append(f"required fields: {', '.join(missing_required)}")
        if missing_optional:
            parts.append(f"optional fields: {', '.join(missing_optional)}")

        prompt = (
            f"A partner onboarding request is missing {', and '.join(parts)}. "
            f"Ask the user to provide them in a friendly, conversational way. "
            f"If there are optional fields mentioned, let them know they can also create the partner with the available data. "
            f"Return only your response text, no markdown, no JSON."
        )

        messages = [
            {"role": "system", "content": "You are a helpful assistant. Respond concisely in 1-2 sentences."},
            {"role": "user", "content": prompt},
        ]

        try:
            return _call_deepseek(messages, temperature=0.3, max_tokens=200, timeout=10)
        except Exception as e:
            logger.warning(f"Failed to generate clarification message: {e}")
            msg = ""
            if missing_required:
                msg += f"Please provide: {', '.join(missing_required)}. "
            if missing_optional:
                msg += f"Optional: {', '.join(missing_optional)} (or create with what we have). "
            return msg.strip()
