from app.assistants.prompts import MAIN_SYSTEM_PROMPT, RAG_SYSTEM_PROMPT
from app.model_manager import model_manager
from app.db import get_chat_messages, add_chat_messages
from app.assistants.tools import QueryKnowledgeBaseTool
from openai import pydantic_function_tool
from time import time
import asyncio
from app.utils.sse_stream import SSEStream
from app.response_reflector import response_reflector
from app.metrics_collector import metrics_collector
from app.ab_testing import ab_testing
import logging

logger = logging.getLogger(__name__)

class RAGAssistant:
    def __init__(self, chat_id, rdb, history_size=30, max_tool_calls=3):
        self.chat_id = chat_id
        self.rdb = rdb
        self.sse_stream = None
        self.main_system_message = {'role': 'system', 'content': MAIN_SYSTEM_PROMPT}
        self.rag_system_message = {'role': 'system', 'content': RAG_SYSTEM_PROMPT}
        self.tools_schema = [pydantic_function_tool(QueryKnowledgeBaseTool)]
        self.history_size = history_size
        self.max_tool_calls = max_tool_calls

    async def _generate_chat_response(self, system_message, chat_messages, **kwargs):
        # استفاده از Model Manager برای انتخاب مدل
        last_message = chat_messages[-1]["content"]
        context_length = sum(len(msg["content"]) for msg in chat_messages)
        model = model_manager.select_model(last_message, context_length)
        
        messages = [system_message, *chat_messages]
        async with model_manager.chat_completion(messages=messages, model=model, **kwargs) as stream:
            async for event in stream:
                if event.type == 'content.delta':
                    await self.sse_stream.send(event.delta)
            final = await stream.get_final_completion()
            return final.choices[0].message

    async def _handle_tool_calls(self, tool_calls, chat_messages):
        any_result = False
        for call in tool_calls[:self.max_tool_calls]:
            try:
                kb_args = call.function.parsed_arguments
                kb_result = await kb_args(self.rdb)
                chat_messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': kb_result})
                if "یافت نشد" not in kb_result:
                    any_result = True
            except Exception as e:
                logger.error(f"Error in tool call: {e}")
                chat_messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': f"خطا در اجرای ابزار: {str(e)}"})

        if any_result:
            return await self._generate_chat_response(
                system_message=self.rag_system_message,
                chat_messages=chat_messages,
            )
        else:
            return {"content": "متأسفانه محصولی مطابق درخواست شما در پایگاه داده پیدا نشد."}

    async def _run_step(self, message, user_id=None):
        start_time = time()
        retrieval_time = 0
        generation_time = 0
        model_used = None
        
        try:
            history = await get_chat_messages(self.rdb, self.chat_id, last_n=self.history_size)
            history.append({'role': 'user', 'content': message})

            # تعیین روش تولید پاسخ بر اساس A/B Testing
            response_variant = ab_testing.get_variant("response_generation", user_id)
            response_config = ab_testing.get_config("response_generation", response_variant)

            assistant_msg = await self._generate_chat_response(
                system_message=self.main_system_message,
                chat_messages=history,
                tools=self.tools_schema,
                tool_choice='auto'
            )
            
            # ذخیره مدل استفاده شده
            model_used = assistant_msg.model if hasattr(assistant_msg, 'model') else "unknown"

            calls = getattr(assistant_msg, 'tool_calls', [])
            if calls:
                history.append({
                    'role': 'assistant',
                    'content': assistant_msg.content or "",
                    'tool_calls': assistant_msg.tool_calls
                })
                retrieval_start = time()
                assistant_msg = await self._handle_tool_calls(calls, history)
                retrieval_time = time() - retrieval_start

            # Self-Reflection اگر در گروه B آزمایش هستیم
            generation_start = time()
            if response_config == "with_reflection":
                context = "\n".join([msg["content"] for msg in history if msg["role"] != "system"])
                refined_content = await response_reflector.reflect(
                    message, 
                    assistant_msg.content, 
                    context
                )
            else:
                refined_content = assistant_msg.content
                
            generation_time = time() - generation_start

            user_db_msg = {'role': 'user', 'content': message, 'created': int(time())}
            assistant_db_msg = {
                'role': 'assistant',
                'content': refined_content,
                'tool_calls': [
                    {'name': tc.function.name, 'arguments': tc.function.arguments} for tc in calls
                ] if calls else [],
                'created': int(time())
            }
            await add_chat_messages(self.rdb, self.chat_id, [user_db_msg, assistant_db_msg])
            
            # ارسال پاسخ نهایی به کاربر
            await self.sse_stream.send(refined_content)
            
        except Exception as e:
            logger.error(f"Error in RAGAssistant: {e}")
            await self.sse_stream.send(f"❌ متأسفانه مشکلی پیش آمد: {e}")
        finally:
            total_time = time() - start_time
            await metrics_collector.record_query_performance(
                message, retrieval_time, generation_time, total_time, model_used
            )
            await self.sse_stream.close()

    async def _handle(self, message, user_id=None):
        try:
            await self._run_step(message, user_id)
        except Exception as e:
            logger.error(f"Error in RAGAssistant._handle: {e}")
            await self.sse_stream.send(f"❌ متأسفانه مشکلی پیش آمد: {e}")
        finally:
            await self.sse_stream.close()

    def run(self, message, user_id=None):
        self.sse_stream = SSEStream()
        asyncio.create_task(self._handle(message, user_id))
        return self.sse_stream