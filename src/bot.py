
import re
import time
import uuid
from src.utils.mastodont import MastodonBot
from src.utils.utils import run_with_retries
from src.agents.agents import Agent
from loguru import logger

class Bot:
    """
    Бот, обрабатывающий запросы на основе рекомендаций от CityVillager и выполняющий функции Mastodon.
    """
    
    CHECK_INTERVAL = 5
    ERROR_SLEEP_TIME = 10

    def __init__(self, mastodon_client: MastodonBot, agent: Agent) -> None:
        self.mastodon_client = mastodon_client
        self.agent = agent
        self.unique_id = uuid.uuid4()


    def start_topic(self, topic: str):
        TOPIC_PROMPT = """Сгенерируй сообщение на тему {topic}. Верни сообщение в формате: Сообщение: <сообщение>"""
        personal_prompt = self.agent.prompt_with_personality(TOPIC_PROMPT).invoke({"topic": topic})

        msg = ""
        while not msg:
            msg = run_with_retries(
                lambda: self.agent.llm.invoke(personal_prompt),
                success_message=None,
                error_message=f"Не удалось сгенерировать сообщение. Сгенерировал: {msg}. Повторная попытка...",
                max_retries=5
            )
            if not "Сообщение: " in msg:
                logger.error(f"Не удалось сгенерировать сообщение. Сгенерировал: {msg}. Повторная попытка...")
                msg = ""
            time.sleep(1)

        msg = msg.replace("Сообщение: ", "")
        
        result = run_with_retries(
            lambda: self.mastodon_client.publish_post(msg),
            success_message=f"Сообщение опубликовано: {msg}",
            error_message=f"Не удалось опубликовать сообщение",
            max_retries=5
        )

        self.agent.update_memory(msg, self.agent.name)

        return result, msg
    
    def add_new_messages(self, new_messages: list):
        for message in new_messages:
            self.agent.update_memory(message['content'], message['username'])

    def clear_memory(self):
        self.agent.clear_memory()

    def topic_step(self, topic_id: int):

        if self.should_reply():
            USER_PROMPT = """Продолжи разговор. Сгенерируй сообщение, органично вписываясь в разговор. Учитывай историю диалога. Это может быть как ответ на конкретное сообщение, так и продолжение раскрытия темы. Верни сообщение в формате: Сообщение: <сообщение>"""
            personal_prompt = self.agent.prompt_with_personality(USER_PROMPT).invoke({"topic": topic_id})
            message = None 

            while not message:
                message = run_with_retries(
                    lambda: self.agent.llm.invoke(personal_prompt),
                    success_message=None,
                    error_message=f"Не удалось сгенерировать сообщение. Сгенерировал: {message}. Повторная попытка...",
                    max_retries=5
                )

                if not "Сообщение: " in message:
                    logger.error(f"Не удалось сгенерировать сообщение. Сгенерировал: {message}. Повторная попытка...")
                    message = None
                time.sleep(1)

            message = message.replace("Сообщение: ", "")

            result = run_with_retries(
                lambda: self.mastodon_client.reply_to_message(topic_id, message),
                success_message=f"Пользователь: {self.agent.name}. Сообщение опубликовано: {message}",
                error_message=f"{self.agent.name}. Не удалось опубликовать сообщение",
                max_retries=5
            )

            self.agent.update_memory(message, self.agent.name)
            return message


    def should_reply(self) -> bool:
        USER_PROMPT = """Оцени следует ли тебе поддержать диалог. Диалог, следует поддержать, если мысль полностью не раскрыта и нужно дополнить её. Если диалог содержит мысли, к которым у твоего персонажа есть неприятие, то не поддерживай диалог. Верни 'Да' или 'Нет'.""" 

        response = None 

        while not response:
            response = run_with_retries(
                lambda: self.agent.llm.invoke(USER_PROMPT),
                success_message=None,
                error_message=f"Произошла ошибка при оценке диалога. Получил: {response}. Повторная попытка...",
                max_retries=5
            )

            if not ("Да" in response or "Нет" in response):
                response = None
                logger.error(f"Не удалось получить ответ. Получил: {response}. Повторная попытка...")
            time.sleep(1)

        logger.info(f"Пользователь: {self.agent.name}. Оценка диалога: {response}")
        return "Да" in response

