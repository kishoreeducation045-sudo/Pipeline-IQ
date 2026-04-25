# app/llm/client.py
import asyncio
import json
import re
from google import genai
from google.genai.errors import APIError
from app.config import settings

def _clean_json(raw: str) -> str:
    """Best-effort cleanup of LLM JSON output."""
    text = raw.strip()
    # Strip markdown fences
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rstrip("`").strip()
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Remove JS-style comments
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    return text


class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    async def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        """Basic text generation. Returns raw string response."""
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=user,
            config=genai.types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        )
        return response.text

    async def generate_with_retry(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        max_attempts: int = 3,
    ) -> str:
        delay = 1.0
        last_err = None
        for attempt in range(max_attempts):
            try:
                return await self.generate(system, user, max_tokens)
            except Exception as e:
                # Catch general API errors for retry logic
                last_err = e
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise
        if last_err is not None:
            raise last_err
        raise RuntimeError("generate_with_retry called with max_attempts=0")

    async def generate_json(
        self,
        system: str,
        user: str,
        schema_model,  # Pydantic model class
        max_tokens: int = 2048,
        max_attempts: int = 3,
    ):
        """Generate, parse JSON, validate against Pydantic model; retry on malformed."""
        last_error = None
        for attempt in range(max_attempts):
            # Tell Gemini to output strictly JSON
            system_json = (
                system
                + "\n\nIMPORTANT: Output ONLY valid JSON. "
                "No trailing commas. No comments. No markdown fences. "
                "Use double quotes for all keys and string values."
            )
            raw = await self.generate_with_retry(system_json, user, max_tokens)

            cleaned = _clean_json(raw)

            try:
                data = json.loads(cleaned)
                return schema_model.model_validate(data)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                if attempt < max_attempts - 1:
                    # Ask Gemini to fix its own output
                    user = (
                        f"Your previous response was not valid JSON. "
                        f"Error: {e}\n\n"
                        f"Original response:\n{raw}\n\n"
                        f"Please return ONLY the corrected, valid JSON without markdown fences."
                    )
        raise last_error  # type: ignore[misc]

gemini = GeminiClient()

