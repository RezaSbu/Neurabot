# app/assistants/assistant.py

import asyncio
from time import time

from openai import pydantic_function_tool
from app.openai import chat_stream
from app.db import get_chat_messages, add_chat_messages
from app.assistants.tools import QueryKnowledgeBaseTool
from app.assistants.prompts import MAIN_SYSTEM_PROMPT, RAG_SYSTEM_PROMPT
from app.utils.sse_stream import SSEStream


class RAGAssistant:
    def __init__(
        self,
        chat_id,
        rdb,
        history_size: int = 30,
        max_tool_calls: int = 3,
        initial_filters: dict | None = None,
    ):
        self.chat_id = chat_id
        self.rdb = rdb
        self.initial_filters = initial_filters or {}
        self.sse_stream: SSEStream | None = None

        self.main_system_message = {"role": "system", "content": MAIN_SYSTEM_PROMPT}
        self.rag_system_message = {"role": "system", "content": RAG_SYSTEM_PROMPT}

        # --- Set up the QueryKnowledgeBaseTool with any initial filters ---
        tool = pydantic_function_tool(QueryKnowledgeBaseTool)
        if self.initial_filters:
            # Merge the filters you extracted (e.g. category, brand, budget…) into the tool call defaults
            tool.function.arguments.update(self.initial_filters)
        self.tools_schema = [tool]

        self.history_size = history_size
        self.max_tool_calls = max_tool_calls

    async def _generate_chat_response(self, system_message, chat_messages, **kwargs):
        messages = [system_message, *chat_messages]
        async with chat_stream(messages=messages, **kwargs) as stream:
            async for event in stream:
                if event.type == "content.delta":
                    await self.sse_stream.send(event.delta)
            final = await stream.get_final_completion()
            return final.choices[0].message

    async def _handle_tool_calls(self, tool_calls, chat_messages):
        any_result = False
        for call in tool_calls[: self.max_tool_calls]:
            # Execute the tool with the merged arguments
            kb_result = await call.function.parsed_arguments(self.rdb)
            chat_messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": kb_result}
            )
            if "یافت نشد" not in kb_result:
                any_result = True

        if any_result:
            return await self._generate_chat_response(
                system_message=self.rag_system_message, chat_messages=chat_messages
            )
        else:
            return {"content": "متأسفانه محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."}

    async def _run_step(self, message: str):
        history = await get_chat_messages(self.rdb, self.chat_id, last_n=self.history_size)
        history.append({"role": "user", "content": message})

        assistant_msg = await self._generate_chat_response(
            system_message=self.main_system_message,
            chat_messages=history,
            tools=self.tools_schema,
            tool_choice="auto",
        )

        calls = getattr(assistant_msg, "tool_calls", [])
        if calls:
            # log the assistant's “thinking” message
            history.append(
                {
                    "role": "assistant",
                    "content": assistant_msg.content or "",
                    "tool_calls": assistant_msg.tool_calls,
                }
            )
            # handle any tool calls and possibly regenerate
            assistant_msg = await self._handle_tool_calls(calls, history)

        # persist both the user and assistant messages
        user_db_msg = {
            "role": "user",
            "content": message,
            "created": int(time()),
        }
        assistant_db_msg = {
            "role": "assistant",
            "content": assistant_msg["content"]
            if isinstance(assistant_msg, dict)
            else assistant_msg.content
            or "",
            "tool_calls": [
                {"name": tc.function.name, "arguments": tc.function.arguments}
                for tc in calls
            ]
            if calls
            else [],
            "created": int(time()),
        }
        await add_chat_messages(self.rdb, self.chat_id, [user_db_msg, assistant_db_msg])

    async def _handle(self, message: str):
        try:
            await self._run_step(message)
        except Exception as e:
            await self.sse_stream.send(f"❌ متأسفانه مشکلی پیش آمد: {e}")
            print(f"Error in RAGAssistant: {e}")
        finally:
            await self.sse_stream.close()

    def run(self, message: str) -> SSEStream:
        """
        Kick off the background task and return the SSE stream immediately.
        """
        self.sse_stream = SSEStream()
        asyncio.create_task(self._handle(message))
        return self.sse_stream
