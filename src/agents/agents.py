from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from typing import Dict
from src.agents.memory import Memory

class Agent:
    def __init__(self, name: str, personality: str, llm = None) -> None:
        self.name = name
        self.personality = personality
        if not llm:
            self.llm = OllamaLLM(base_url="http://a3l.maas:33333", model="ilyagusev/saiga_llama3:latest")
        else:
            self.llm = llm

        self.memory = Memory(k=20)
    
    def update_memory(self, message: str, name: str):
        self.memory.add_message(message, name)

    def clear_memory(self):
        self.memory.clear()

    def create_personality_prompt(self) -> str:
        personality = self.personality
        return f"""Ты - пользователь социальной сети. Тебя зовут {self.name}. Твой характер: {personality}. Ты должен четко следовать этому характеру. Используй только русский язык.\n. Делай сообщения не больше 490 символов. История сообщений: {self.memory.get_history()} """
    
    def prompt_with_personality(self, prompt: str):
        return ChatPromptTemplate.from_messages([
            ("system", self.create_personality_prompt()),
            ("user", prompt)
        ])
