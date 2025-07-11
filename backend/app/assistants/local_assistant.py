import asyncio
from rich.console import Console
from openai import pydantic_function_tool
from app.db import get_redis
from app.openai import chat_stream
from app.assistants.tools import QueryKnowledgeBaseTool
from app.assistants.prompts import MAIN_SYSTEM_PROMPT, RAG_SYSTEM_PROMPT

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
        messages = [system_message, *chat_messages]
        async with chat_stream(messages=messages, **kwargs) as stream:
            async for event in stream:
                if event.type == 'content.delta':
                    self.console.print(event.delta, style='cyan', end='')
            final = await stream.get_final_completion()
            if final.choices[0].message.content:
                self.console.print()
            return final.choices[0].message

    async def run(self):
        async with get_redis() as rdb:
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
                        kb_res = await call.function.parsed_arguments(rdb)
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

                self.chat_history.extend([user_msg, {'role': 'assistant', 'content': assistant_msg['content'] if isinstance(assistant_msg, dict) else assistant_msg.content}])
                self.console.print("\n🔁 گفتگو ادامه دارد...")

async def main():
    assistant = LocalRAGAssistant()
    await assistant.run()

if __name__ == '__main__':
    asyncio.run(main())
