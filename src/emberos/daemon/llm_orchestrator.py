"""
LLM Orchestrator for EmberOS.

Manages connection to llama.cpp server and handles all LLM interactions
including completion requests, streaming, and model management.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional
from dataclasses import dataclass

import aiohttp

from emberos.core.config import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class CompletionRequest:
    """LLM completion request."""
    prompt: str
    max_tokens: int = 2048
    temperature: float = 0.1
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop: list[str] = None
    stream: bool = False

    def __post_init__(self):
        if self.stop is None:
            self.stop = ["</s>", "User:", "Human:"]


@dataclass
class CompletionResponse:
    """LLM completion response."""
    content: str
    tokens_used: int
    finish_reason: str
    model: str


class LLMOrchestrator:
    """
    Orchestrates LLM interactions for EmberOS.

    Connects to a llama.cpp server via HTTP API and provides
    methods for generating completions and streaming responses.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        self._model_name: Optional[str] = None
        self._model_info: dict = {}

    async def start(self) -> None:
        """Start the LLM orchestrator."""
        logger.info("Starting LLM orchestrator...")

        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # Check connection and get model info
        await self._check_connection()

    async def stop(self) -> None:
        """Stop the LLM orchestrator."""
        logger.info("Stopping LLM orchestrator...")

        if self.session:
            await self.session.close()
            self.session = None

        self._connected = False

    async def _check_connection(self) -> bool:
        """Check connection to LLM server."""
        try:
            async with self.session.get(f"{self.config.server_url}/health") as resp:
                if resp.status == 200:
                    self._connected = True

                    # Try to get model info
                    try:
                        async with self.session.get(f"{self.config.server_url}/v1/models") as model_resp:
                            if model_resp.status == 200:
                                data = await model_resp.json()
                                if data.get("data"):
                                    self._model_info = data["data"][0]
                                    self._model_name = self._model_info.get("id", "Unknown")
                    except Exception:
                        self._model_name = "llama.cpp"

                    logger.info(f"Connected to LLM server: {self._model_name}")
                    return True

        except aiohttp.ClientError as e:
            logger.warning(f"LLM server not available: {e}")
            self._connected = False
        except Exception as e:
            logger.error(f"Error checking LLM connection: {e}")
            self._connected = False

        return False

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate a completion from the LLM.

        Args:
            request: Completion request parameters

        Returns:
            CompletionResponse with generated content
        """
        if not self._connected:
            await self._check_connection()
            if not self._connected:
                raise ConnectionError("LLM server not available")

        payload = {
            "prompt": request.prompt,
            "n_predict": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "repeat_penalty": request.repeat_penalty,
            "stop": request.stop,
            "stream": False,
        }

        try:
            async with self.session.post(
                f"{self.config.server_url}/completion",
                json=payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"LLM server error: {error_text}")

                data = await resp.json()

                return CompletionResponse(
                    content=data.get("content", ""),
                    tokens_used=data.get("tokens_evaluated", 0) + data.get("tokens_predicted", 0),
                    finish_reason=data.get("stop_type", "unknown"),
                    model=self._model_name or "unknown"
                )

        except aiohttp.ClientError as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to LLM server: {e}")

    async def complete_chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Generate a chat completion using message format.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: Optional system prompt
            **kwargs: Additional completion parameters

        Returns:
            CompletionResponse with generated content
        """
        # Build prompt from messages
        prompt_parts = []

        if system_prompt:
            prompt_parts.append(f"<|im_start|>system\n{system_prompt}<|im_end|>")

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            prompt_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")

        # Add assistant start
        prompt_parts.append("<|im_start|>assistant\n")

        prompt = "\n".join(prompt_parts)

        request = CompletionRequest(
            prompt=prompt,
            stop=["<|im_end|>", "<|im_start|>"],
            **kwargs
        )

        return await self.complete(request)

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """
        Stream completion tokens from the LLM.

        Args:
            request: Completion request parameters

        Yields:
            String tokens as they are generated
        """
        if not self._connected:
            await self._check_connection()
            if not self._connected:
                raise ConnectionError("LLM server not available")

        payload = {
            "prompt": request.prompt,
            "n_predict": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "repeat_penalty": request.repeat_penalty,
            "stop": request.stop,
            "stream": True,
        }

        try:
            async with self.session.post(
                f"{self.config.server_url}/completion",
                json=payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"LLM server error: {error_text}")

                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if content := data.get("content"):
                            yield content
                        if data.get("stop"):
                            break

        except aiohttp.ClientError as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to LLM server: {e}")

    async def generate_json(
        self,
        prompt: str,
        schema: Optional[dict] = None,
        **kwargs
    ) -> dict:
        """
        Generate a JSON response from the LLM.

        Args:
            prompt: The prompt requesting JSON output
            schema: Optional JSON schema for validation
            **kwargs: Additional completion parameters

        Returns:
            Parsed JSON dictionary
        """
        # Add JSON instruction to prompt
        json_prompt = f"""{prompt}

Respond with valid JSON only. No markdown, no explanation, just the JSON object."""

        request = CompletionRequest(
            prompt=json_prompt,
            **kwargs
        )

        response = await self.complete(request)
        content = response.content.strip()

        # Try to extract JSON from response
        if content.startswith("```"):
            # Remove markdown code blocks
            lines = content.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                elif in_block or not line.startswith("```"):
                    json_lines.append(line)
            content = "\n".join(json_lines)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {content[:200]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if connected to LLM server."""
        return self._connected

    @property
    def model_name(self) -> Optional[str]:
        """Get current model name."""
        return self._model_name

    @property
    def model_info(self) -> dict:
        """Get model information."""
        return self._model_info

    async def get_stats(self) -> dict:
        """Get LLM server statistics."""
        if not self._connected:
            return {"status": "disconnected"}

        try:
            async with self.session.get(f"{self.config.server_url}/health") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"Failed to get LLM stats: {e}")

        return {"status": "unknown"}

