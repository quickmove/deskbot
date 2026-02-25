"""
LLM (Large Language Model) module

Supports:
- OpenAI API (GPT models)
- MiniMax API (M2.5 model, Anthropic compatible)
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass, field

from server.config.settings import config

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Chat message"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    thinking: Optional[str] = None  # MiniMax specific
    usage: Optional[Dict[str, Any]] = None


class LLM:
    """LLM wrapper supporting multiple providers"""

    def __init__(self, llm_config=None):
        """
        Initialize LLM

        Args:
            llm_config: LLMConfig instance, uses global config if None
        """
        self.config = llm_config or config.llm
        self._client = None

        logger.info(
            f"LLM initialized: provider={self.config.provider}, "
            f"model={self.config.model}"
        )

    def _ensure_client(self):
        """Lazy initialize the client"""
        if self._client is None:
            if self.config.provider == "minimax":
                # MiniMax uses Anthropic SDK
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url
                )
            else:
                # OpenAI
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url
                )

    async def chat(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> LLMResponse:
        """
        Send chat request to LLM

        Args:
            messages: List of chat messages
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            stream: Enable streaming

        Returns:
            LLMResponse with content
        """
        self._ensure_client()

        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens

        # Convert messages to dict format
        msg_list = [{"role": m.role, "content": m.content} for m in messages]

        try:
            if self.config.provider == "minimax":
                return await self._chat_minimax(
                    messages=msg_list,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                return await self._chat_openai(
                    messages=msg_list,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            return LLMResponse(content=f"Error: {str(e)}")

    async def _chat_minimax(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Chat with MiniMax API"""
        # Build request
        request_params = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "messages": []
        }

        if system:
            request_params["system"] = system

        # Add messages
        for msg in messages:
            request_params["messages"].append({
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}]
            })

        response = await asyncio.to_thread(
            self._client.messages.create,
            **request_params
        )

        # Parse response
        content = ""
        thinking = None

        for block in response.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                content += block.text

        return LLMResponse(
            content=content.strip(),
            thinking=thinking
        )

    async def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Chat with OpenAI API"""
        # Build request
        messages_with_system = []
        if system:
            messages_with_system.append({"role": "system", "content": system})
        messages_with_system.extend(messages)

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages_with_system,
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content or ""

        return LLMResponse(content=content.strip())

    async def chat_stream(
        self,
        messages: List[Message],
        system: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream chat response

        Args:
            messages: List of chat messages
            system: System prompt

        Yields:
            Response text chunks
        """
        self._ensure_client()

        msg_list = [{"role": m.role, "content": m.content} for m in messages]

        try:
            if self.config.provider == "minimax":
                # MiniMax doesn't support streaming in the same way
                response = await self.chat(messages, system=system)
                yield response.content
            else:
                # OpenAI streaming
                messages_with_system = []
                if system:
                    messages_with_system.append({"role": "system", "content": system})
                messages_with_system.extend(msg_list)

                stream = await self._client.chat.completions.create(
                    model=self.config.model,
                    messages=messages_with_system,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=True
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield f"Error: {str(e)}"


# Global LLM instance
_llm_instance: Optional[LLM] = None


def get_llm() -> LLM:
    """Get global LLM instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLM()
    return _llm_instance
