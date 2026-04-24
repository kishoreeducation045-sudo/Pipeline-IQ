# app/llm/client.py
import asyncio
import json
from anthropic import AsyncAnthropic, APIError, RateLimitError
from app.config import settings

class ClaudeClient:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    async def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        """Basic text generation. Returns raw string response."""
        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Response is a list of content blocks; we extract text blocks
        return "".join(
            block.text for block in msg.content if block.type == "text"
        )

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
            except RateLimitError as e:
                last_err = e
                await asyncio.sleep(delay)
                delay *= 2
            except APIError as e:
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
        max_attempts: int = 2,
    ):
        """Generate, parse JSON, validate against Pydantic model; retry once on malformed."""
        for attempt in range(max_attempts):
            raw = await self.generate_with_retry(system, user, max_tokens)
            # Strip optional ```json fences
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```", 2)[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.rstrip("`").strip()
            try:
                data = json.loads(cleaned)
                return schema_model.model_validate(data)
            except (json.JSONDecodeError, ValueError) as e:
                if attempt == max_attempts - 1:
                    raise
                # Ask Claude to fix its own output
                user = (
                    f"Your previous response was not valid JSON matching the required schema. "
                    f"Error: {e}\n\n"
                    f"Original response:\n{raw}\n\n"
                    f"Please return ONLY the corrected JSON, no prose, no code fences."
                )

claude = ClaudeClient()
