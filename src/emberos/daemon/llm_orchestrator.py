"""
LLM Orchestrator for EmberOS.

Manages connection to llama.cpp/BitNet server and handles all LLM interactions
including completion requests, streaming, and model management.

Supports dual-model architecture:
- BitNet for fast text-only tasks
- Qwen2.5-VL for vision tasks (images, PDFs, screenshots)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional
from dataclasses import dataclass
from enum import Enum

import aiohttp

from emberos.core.config import LLMConfig

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """LLM model types."""
    TEXT = "text"  # Fast text-only model (BitNet)
    VISION = "vision"  # Vision-language model (Qwen2.5-VL)


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
    model_type: ModelType = ModelType.TEXT  # Default to fast text model
    has_images: bool = False  # Whether request includes images

    def __post_init__(self):
        if self.stop is None:
            self.stop = ["</s>", "User:", "Human:"]

        # Auto-select vision model if images present
        if self.has_images:
            self.model_type = ModelType.VISION


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

    Connects to two llama.cpp servers:
    - BitNet (port 8080) for fast text-only tasks
    - Qwen2.5-VL (port 11434) for vision tasks

    Automatically routes requests based on task requirements.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

        # Dual model setup
        # Use config.server_url for BitNet (text model), default to 38080 if not set properly
        self._text_url = self.config.server_url or "http://127.0.0.1:38080"
        self._vision_url = "http://127.0.0.1:11434"  # Qwen2.5-VL

        self._text_connected = False
        self._vision_connected = False

        self._text_model_name: Optional[str] = None
        self._vision_model_name: Optional[str] = None

    async def start(self) -> None:
        """Start the LLM orchestrator."""
        logger.info("Starting LLM orchestrator...")

        # Use 120s timeout from config
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # Check connection to both models
        await self._check_text_model()
        await self._check_vision_model()

        if not self._text_connected and not self._vision_connected:
            logger.error("No LLM servers available!")
        elif not self._text_connected:
            logger.warning(f"BitNet text model not available at {self._text_url}, will use vision model for all tasks")
        elif not self._vision_connected:
            logger.warning("Vision model not available, image tasks will fail")

    async def stop(self) -> None:
        """Stop the LLM orchestrator."""
        logger.info("Stopping LLM orchestrator...")

        if self.session:
            await self.session.close()
            self.session = None

        self._text_connected = False
        self._vision_connected = False

    async def _check_text_model(self) -> bool:
        """Check connection to BitNet text model."""
        try:
            async with self.session.get(f"{self._text_url}/health") as resp:
                if resp.status == 200:
                    self._text_connected = True

                    try:
                        async with self.session.get(f"{self._text_url}/v1/models") as model_resp:
                            if model_resp.status == 200:
                                data = await model_resp.json()
                                if data.get("data"):
                                    self._text_model_name = data["data"][0].get("id", "BitNet")
                    except Exception:
                        self._text_model_name = "BitNet"

                    logger.info(f"Connected to text model: {self._text_model_name} at {self._text_url}")
                    return True
        except Exception as e:
            logger.debug(f"Text model not available at {self._text_url}: {e}")
            self._text_connected = False

        return False

    async def _check_vision_model(self) -> bool:
        """Check connection to Qwen2.5-VL vision model."""
        try:
            async with self.session.get(f"{self._vision_url}/health") as resp:
                if resp.status == 200:
                    self._vision_connected = True

                    try:
                        async with self.session.get(f"{self._vision_url}/v1/models") as model_resp:
                            if model_resp.status == 200:
                                data = await model_resp.json()
                                if data.get("data"):
                                    self._vision_model_name = data["data"][0].get("id", "Qwen2.5-VL")
                    except Exception:
                        self._vision_model_name = "Qwen2.5-VL"

                    logger.info(f"Connected to vision model: {self._vision_model_name} (port 11434)")
                    return True
        except Exception as e:
            logger.debug(f"Vision model not available: {e}")
            self._vision_connected = False

        return False

    def _get_server_url(self, model_type: ModelType) -> str:
        """Get appropriate server URL based on model type."""
        if model_type == ModelType.VISION:
            return self._vision_url
        return self._text_url

    def _is_model_available(self, model_type: ModelType) -> bool:
        """Check if requested model is available."""
        if model_type == ModelType.TEXT:
            return self._text_connected
        elif model_type == ModelType.VISION:
            return self._vision_connected
        return False

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate a completion from the LLM.
        Automatically routes to appropriate model (BitNet or Qwen2.5-VL).

        Args:
            request: Completion request parameters

        Returns:
            CompletionResponse with generated content
        """
        # Determine which model to use
        model_type = request.model_type
        server_url = self._get_server_url(model_type)

        # Check model availability and fallback
        if model_type == ModelType.TEXT and not self._text_connected:
            if self._vision_connected:
                logger.info("[ORCHESTRATOR] BitNet not available, routing to Qwen2.5-VL")
                model_type = ModelType.VISION
                server_url = self._vision_url
            else:
                # Try to reconnect first
                await self._check_text_model()
                await self._check_vision_model()

                if self._text_connected:
                    server_url = self._text_url
                elif self._vision_connected:
                    model_type = ModelType.VISION
                    server_url = self._vision_url
                else:
                    raise ConnectionError("No LLM servers available")

        elif model_type == ModelType.VISION and not self._vision_connected:
            if self._text_connected and not request.has_images:
                logger.info("[ORCHESTRATOR] Qwen2.5-VL not available, routing text to BitNet")
                model_type = ModelType.TEXT
                server_url = self._text_url
            else:
                raise ConnectionError("Vision model not available for image processing")

        logger.info(f"[ORCHESTRATOR] Routing request to {model_type.value} model at {server_url}")

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

        logger.info(f"Sending request to {server_url}/completion with payload size {len(json.dumps(payload))} bytes")
        
        try:
            logger.debug("Starting request...")
            # Use configurable timeout (default 120s) instead of hardcoded 30s
            request_timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with self.session.post(
                f"{server_url}/completion",
                json=payload,
                headers={"Connection": "close"},
                timeout=request_timeout
            ) as resp:
                logger.debug(f"Response status: {resp.status}")
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"LLM server error: {error_text}")

                data = await resp.json()
                logger.debug("Response JSON parsed")

                model_name = self._text_model_name if model_type == ModelType.TEXT else self._vision_model_name
                logger.info(f"Received response from {model_type.value} model: {len(data.get('content', ''))} chars")
                return CompletionResponse(
                    content=data.get("content", ""),
                    tokens_used=data.get("tokens_evaluated", 0) + data.get("tokens_predicted", 0),
                    finish_reason=data.get("stop_type", "unknown"),
                    model=model_name or "unknown"
                )

        except asyncio.TimeoutError:
            logger.error(f"Request to {model_type.value} model timed out after {self.config.timeout}s - server may be hung")
            # Mark model as disconnected so future requests fallback
            if model_type == ModelType.TEXT:
                self._text_connected = False
                logger.warning("Marking BitNet as disconnected - will fallback to Qwen")
            raise ConnectionError(f"{model_type.value} model timed out")
        except aiohttp.ClientError as e:
            logger.error(f"Error connecting to LLM server ({model_type}): {e}")
            raise ConnectionError(f"Failed to connect to LLM server: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in complete(): {e}")
            raise e

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
        # Determine which model to use
        model_type = request.model_type
        server_url = self._get_server_url(model_type)

        # Check if model is available
        if not self._is_model_available(model_type):
            if model_type == ModelType.TEXT and self._vision_connected:
                logger.info("Text model unavailable, using vision model for streaming")
                server_url = self._vision_url
            else:
                raise ConnectionError("No LLM servers available for streaming")

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
                f"{server_url}/completion",
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
            logger.error(f"Error connecting to LLM server ({model_type}): {e}")
            # Don't permanently disable model on one error
            # if model_type == ModelType.TEXT:
            #     self._text_connected = False
            # else:
            #     self._vision_connected = False
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
        """Check if connected to any LLM server."""
        return self._text_connected or self._vision_connected

    @property
    def model_name(self) -> Optional[str]:
        """Get current primary model name."""
        if self._text_connected:
            return self._text_model_name
        elif self._vision_connected:
            return self._vision_model_name
        return None

    @property
    def model_info(self) -> dict:
        """Get model information."""
        return {
            "text_model": {
                "name": self._text_model_name,
                "connected": self._text_connected,
                "url": self._text_url
            },
            "vision_model": {
                "name": self._vision_model_name,
                "connected": self._vision_connected,
                "url": self._vision_url
            }
        }

    async def get_stats(self) -> dict:
        """Get LLM server statistics."""
        stats = {
            "text_model": {"status": "disconnected"},
            "vision_model": {"status": "disconnected"}
        }

        if self._text_connected:
            try:
                async with self.session.get(f"{self._text_url}/health") as resp:
                    if resp.status == 200:
                        stats["text_model"] = await resp.json()
                        stats["text_model"]["status"] = "connected"
            except Exception as e:
                logger.warning(f"Failed to get text model stats: {e}")

        if self._vision_connected:
            try:
                async with self.session.get(f"{self._vision_url}/health") as resp:
                    if resp.status == 200:
                        stats["vision_model"] = await resp.json()
                        stats["vision_model"]["status"] = "connected"
            except Exception as e:
                logger.warning(f"Failed to get vision model stats: {e}")

        return stats

