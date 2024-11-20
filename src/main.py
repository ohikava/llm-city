import json
import random
import threading
import time

from langchain_ollama import OllamaLLM
from src.bot import Bot
from src.agents.agents import Agent
from src.utils.mastodont import MastodonBot
from src.utils.utils import run_with_retries
from loguru import logger

class MainExecutor:

    TOPIC_MAX_MESSAGES = 20
    def __init__(self, model: str) -> None:
        self.model = model

        self.agents: list[Bot] = []
        self.load_agents()

        self.current_topic = ""
        self.topic_id = None 
        self.messages_count = 0

        self.saved_messages_ids = set()


    def load_agents(self):
        with open("profiles.json", "r") as f:
            profiles = json.load(f)

        for profile in profiles:
            mastodon_client = MastodonBot(profile['access_token'])
            agent = Agent(mastodon_client.name, profile['profile'], OllamaLLM(base_url=profile['url'], model=self.model))
            bot = Bot(mastodon_client, agent)
            self.agents.append(bot)

    def should_change_topic(self):
        return not self.current_topic or self.messages_count > self.TOPIC_MAX_MESSAGES
    
    def generate_topic(self):
        topic = None
        GENERATE_TOPIC_PROMPT = """Придумай тему для разговора. Верни тему в формате: Тема: <тема>"""

        while not topic:
            topic = run_with_retries(
                lambda: self.agents[0].agent.llm.invoke(GENERATE_TOPIC_PROMPT),
                success_message=None,
                error_message="Возникла ошибка при генерации темы",
                max_retries=5
            )

            if "Тема: " not in topic:
                topic = None
                logger.error("Не удаеться сгенерировать тему. Повторная попытка...")

        time.sleep(1)

        topic = topic.replace("Тема: ", "")
        logger.info(f"Сгенерирована тема: {topic}")
        
        self.current_topic = topic

        return topic
    def update_agents_memory_manual(self, agent_to_exclude: Bot, new_messages: list):
        for _ in new_messages:
            self.messages_count += 1

        def add_messages(agent: Bot, new_replies: list):
            agent.add_new_messages(new_replies)
        threads = []
        for agent in self.agents:
            if agent == agent_to_exclude:
                continue
            thread = threading.Thread(target=add_messages, args=(agent, new_messages))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        logger.info(f"Добавлены новые сообщения в память агентов. Количество новых сообщений: {len(new_messages)}")

        
    def update_agents_memory(self, agent_to_exclude: Bot):
        if agent_to_exclude:
            replies = agent_to_exclude.mastodon_client.fetch_notifications()
            new_messages = []
            for reply in replies:
                if reply['id'] not in self.saved_messages_ids:
                    self.saved_messages_ids.add(reply['id'])
                    new_messages.append(reply)
                else:
                    break 
            if new_messages:
                self.update_agents_memory_manual(agent_to_exclude, new_messages)

                        
    def start(self):
        logger.info("Запуск симуляции...")
        agent_to_exclude = None

        while True:
            self.update_agents_memory(agent_to_exclude)

            if self.should_change_topic():
                for agent in self.agents:
                    agent.clear_memory()

                logger.info("Генерация новой темы...")
                self.generate_topic()
                self.messages_count = 0

                random_agent: Bot = random.choice(self.agents)
                result, message = random_agent.start_topic(self.current_topic)
                self.topic_id = result['id']

                agent_to_exclude = random_agent
                self.update_agents_memory_manual(agent_to_exclude, [{"content": message, "username": random_agent.agent.name}])
                

            shuffled_agents = self.agents.copy()
            random.shuffle(shuffled_agents)

            for agent in shuffled_agents:
                if agent == agent_to_exclude:
                    continue

                message = agent.topic_step(self.topic_id)
                self.update_agents_memory_manual(agent, [{"content": message, "username": agent.agent.name}])
            agent_to_exclude = agent 

            time.sleep(1)