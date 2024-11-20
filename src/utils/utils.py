import re 
from loguru import logger

def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Удаляет предложения с конца текста до тех пор, пока его длина не станет меньше max_length.
    Предложения могут заканчиваться не только точкой.
    """
    sentences = re.split(r'(?<=[.!?]) +', text)  # Разделяем текст на предложения
    while len(' '.join(sentences)) >= max_length and sentences:
        sentences.pop()  # Удаляем последнее предложение
    return ' '.join(sentences)

def run_with_retries(func, success_message: str = None, error_message: str = None, max_retries: int = 5):
    attempts = 0
    while attempts < max_retries:
        try:
            result = func()
            if success_message:
                logger.info(success_message)
            return result
        except Exception as e:
            attempts += 1
            if error_message:
                logger.error(f"{error_message}. Попытка {attempts}/{max_retries}. Ошибка: {e}")
            if attempts >= max_retries:
                raise e  # Re-raise the last exception after max retries