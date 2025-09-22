import asyncio
from rich.console import Console
from openai import pydantic_function_tool
from app.redis_client import get_redis
from app.model_manager import model_manager
from app.query_processor import query_processor
from app.response_reflector import response_reflector
from app.assistants.tools import QueryKnowledgeBaseTool
from app.assistants.prompts import MAIN_SYSTEM_PROMPT, RAG_SYSTEM_PROMPT
from app.metrics_collector import metrics_collector

class LocalRAGAssistant:
    def __init__(self, history_size=30, max_tool_calls=3, log_tool_calls=True, log_tool_results=True):
        self.console = Console()
        self.chat_history = []
        self.main_system_message = {'role': 'system', 'content': MAIN_SYSTEM_PROMPT}
        self.rag_system_message = {'role': 'system', 'content': RAG_SYSTEM_PROMPT}
        self.history_size = history_size
        self.max_tool_calls = max_tool_calls
        self.log_tool_calls = log_tool_calls
        self.log_tool_results = log_tool_results

    async def _generate_chat_response(self, system_message, chat_messages, **kwargs):
        last_message = chat_messages[-1]["content"]
        context_length = sum(len(msg["content"]) for msg in chat_messages)
        model = model_manager.select_model(last_message, context_length)
        
        messages = [system_message, *chat_messages]
        response = ""
        
        async with model_manager.chat_completion(messages=messages, model=model, **kwargs) as stream:
            async for event in stream:
                if event.type == 'content.delta':
                    self.console.print(event.delta, style='cyan', end='')
                    response += event.delta
            if response:
                self.console.print()
            final = await stream.get_final_completion()
            return final.choices[0].message

    async def run(self):
        rdb = get_redis()
        try:
            self.console.print('NeuraQueen در خدمت شماست! 😊 بفرمایید سؤال بعدی؟', style='green')
            while True:
                chat_hist = self.chat_history[-self.history_size:]
                user_input = input('\n> ')
                self.console.print()
                if user_input.strip().lower() in ["/exit", "خروج"]:
                    print("خدانگهدار! 👋")
                    break

                user_msg = {'role': 'user', 'content': user_input}
                chat_hist.append(user_msg)

                processed_query = await query_processor.process_query(user_input)
                
                if len(processed_query["sub_queries"]) > 1:
                    self.console.print(f"[yellow]تحلیل کوئری: {len(processed_query['sub_queries'])} زیرسوال شناسایی شد[/yellow]")
                    for i, sub_query in enumerate(processed_query["sub_queries"], 1):
                        self.console.print(f"[dim]{i}. {sub_query}[/dim]")

                assistant_msg = await self._generate_chat_response(
                    system_message=self.main_system_message,
                    chat_messages=chat_hist,
                    tools=[pydantic_function_tool(QueryKnowledgeBaseTool)],
                    tool_choice='auto'
                )

                calls = getattr(assistant_msg, 'tool_calls', [])
                if calls:
                    chat_hist.append({'role': 'assistant', 'content': assistant_msg.content or ""})
                    any_result = False
                    for call in calls[:self.max_tool_calls]:
                        if self.log_tool_calls:
                            self.console.print(f"\n[tool call] {call.to_dict()}", style='yellow')
                        
                        kb_args = call.function.parsed_arguments
                        kb_args.query_input = processed_query["original_query"]
                        kb_res = await kb_args(rdb)
                        
                        if "یافت نشد" not in kb_res:
                            any_result = True
                        if self.log_tool_results:
                            self.console.print(f"\n[tool result]\n{kb_res}\n", style='magenta')
                        chat_hist.append({'role': 'tool', 'tool_call_id': call.id, 'content': kb_res})
                    
                    if any_result:
                        assistant_msg = await self._generate_chat_response(
                            system_message=self.rag_system_message,
                            chat_messages=chat_hist,
                        )
                    else:
                        assistant_msg = {"content": "متأسفانه محصولی مطابق درخواست شما در پایگاه داده موجود نیست."}

                context = "\n".join([msg["content"] for msg in chat_hist if msg["role"] != "system"])
                refined_content = await response_reflector.reflect(
                    user_input, 
                    assistant_msg.content if isinstance(assistant_msg, dict) else assistant_msg.content, 
                    context
                )
                
                self.console.print(f"\n[cyan][bold]پاسخ نهایی:[/bold][/cyan]")
                self.console.print(refined_content)
                
                feedback = input("\nآیا پاسخ مفید بود؟ (بله/خیر/نظردادن): ").strip().lower()
                if feedback in ["بله", "خیر"]:
                    feedback_type = "positive" if feedback == "بله" else "negative"
                    comment = input("توضیحات بیشتر (اختیاری): ")
                    await metrics_collector.record_user_feedback(
                        "local_chat", 
                        str(len(self.chat_history)), 
                        feedback_type, 
                        comment if comment else None
                    )

                self.chat_history.extend([
                    user_msg, 
                    {'role': 'assistant', 'content': refined_content}
                ])
                self.console.print("\n🔁 گفتگو ادامه دارد...")
        finally:
            await rdb.close()  # اصلاح این خط

async def main():
    assistant = LocalRAGAssistant()
    await assistant.run()

if __name__ == '__main__':
    asyncio.run(main())