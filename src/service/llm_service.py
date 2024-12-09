import importlib
from collections.abc import AsyncIterator
from dataclasses import field
from functools import cached_property
from typing import Optional, Union, Type, Any

from langchain_core.language_models import BaseChatModel, BaseLLM
from langchain_core.messages import AIMessageChunk, SystemMessage, HumanMessage
from loguru import logger
from pydantic import BaseModel


class LLMConfig(BaseModel):
    llm_class_path: str
    llm_kwargs: dict[str, Any]
    stop_words: Optional[list[str]] = None
    allowed_tools_regexps: list[str] = field(default_factory=list)


class LLMService:
    def __init__(self, llm_config: LLMConfig) -> None:
        self.llm_config = llm_config
        self.DEFAULT_SYSTEM_PROMPT = "You're a helpful assistant"

    @cached_property
    def _llm(self) -> Union[BaseLLM, BaseChatModel]:
        try:
            module_name, class_name = self.llm_config.llm_class_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            llm_class = getattr(module, class_name)
        except AttributeError as e:
            raise ValueError(
                f"LLM class {self.llm_config.llm_class_path} not found"
            ) from e

        if not issubclass(llm_class, BaseLLM) and not issubclass(
            llm_class, BaseChatModel
        ):
            raise ValueError(
                f"Class {self.llm_config.llm_class_path} has to be of type BaseChatModel or BaseLLM"
            )
        try:
            return llm_class(**self.llm_config.llm_kwargs)
        except Exception as e:
            raise ValueError(f"Error while creating LLM {llm_class}: {e}") from e

    def _prepare_messages(self, prompt: str, system_prompt: Optional[str] = None):
        """Prepare messages list with optional system prompt."""
        messages = []
        if isinstance(self._llm, BaseChatModel):
            messages.append(
                SystemMessage(content=system_prompt or self.DEFAULT_SYSTEM_PROMPT)
            )
        messages.append(HumanMessage(content=prompt))
        return messages

    def _prepare_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Prepare prompt string with optional system prompt for non-chat models."""
        if isinstance(self._llm, BaseLLM):
            return f"{system_prompt or self.DEFAULT_SYSTEM_PROMPT}\n\n{prompt}"
        return prompt

    async def astream_llm(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        logger.debug(f"Prompting in stream mode LLM {self._llm.name} with: {prompt}")

        if isinstance(self._llm, BaseChatModel):
            messages = self._prepare_messages(prompt, system_prompt)
            async for chunk in self._llm.astream(
                input=messages, stop=self.llm_config.stop_words
            ):
                yield chunk.content
        else:
            prepared_prompt = self._prepare_prompt(prompt, system_prompt)
            async for chunk in self._llm.astream(
                input=prepared_prompt, stop=self.llm_config.stop_words
            ):
                yield chunk.content

    async def aprompt_llm(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        logger.debug(f"Prompting LLM {self._llm.name} with: {prompt}")

        if isinstance(self._llm, BaseChatModel):
            messages = self._prepare_messages(prompt, system_prompt)
            answer = await self._llm.ainvoke(
                input=messages, stop=self.llm_config.stop_words
            )
        else:
            prepared_prompt = self._prepare_prompt(prompt, system_prompt)
            answer = await self._llm.ainvoke(
                input=prepared_prompt, stop=self.llm_config.stop_words
            )

        if hasattr(answer, "content"):
            answer = answer.content
        logger.debug(f"LLM answer: {answer}")
        return answer

    def prompt_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        logger.debug(f"Prompting LLM {self._llm.name} with: {prompt}")

        if isinstance(self._llm, BaseChatModel):
            messages = self._prepare_messages(prompt, system_prompt)
            answer = self._llm.invoke(input=messages, stop=self.llm_config.stop_words)
        else:
            prepared_prompt = self._prepare_prompt(prompt, system_prompt)
            answer = self._llm.invoke(
                input=prepared_prompt, stop=self.llm_config.stop_words
            )

        if hasattr(answer, "content"):
            answer = answer.content
        logger.debug(f"LLM answer: {answer}")
        return answer

    def prompt_with_structure(
        self,
        prompt: str,
        response_model: Type["BaseModel"],
        system_prompt: Optional[str] = None,
    ) -> "BaseModel":
        logger.debug(f"Prompting LLM {self._llm.name} with: {prompt}")
        llm_with_structure = self._llm.with_structured_output(response_model)

        if isinstance(self._llm, BaseChatModel):
            messages = self._prepare_messages(prompt, system_prompt)
            answer = llm_with_structure.invoke(
                input=messages, stop=self.llm_config.stop_words
            )
        else:
            prepared_prompt = self._prepare_prompt(prompt, system_prompt)
            answer = llm_with_structure.invoke(
                input=prepared_prompt, stop=self.llm_config.stop_words
            )

        logger.debug(f"LLM answer: {answer}")
        return answer
