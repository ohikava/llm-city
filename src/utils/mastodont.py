import bs4
from loguru import logger
from mastodon import MastodonError, Mastodon

from src.utils.utils import truncate_text

class MastodonBot:
    """
    Класс для работы с API Mastodon.
    """
    def __init__(self, access_token: str) -> None:
        self.mastodon_client = Mastodon(
            access_token=access_token,
            api_base_url="https://mastodon.itiabd.online"
        )
        self.last_notification_time = None
        self.last_notification_id = None
        self.last_timeline_id = None
        self.last_timeline_time = None

        self.name = self.mastodon_client.account_verify_credentials()["username"]

    def update_profile_name(self, new_display_name: str) -> str:
        return self.mastodon_client.account_update_credentials(display_name=new_display_name)

    def publish_post(self, post_text: str) -> str:
        post_text = truncate_text(post_text)

        return self.mastodon_client.status_post(post_text)

    def reply_to_message(self, message_id: int, reply_text: str) -> str:
        reply_text = truncate_text(reply_text)
        return self.mastodon_client.status_post(reply_text, in_reply_to_id=message_id)
    def reply_with_tag(self, username: str, message_id: int, reply_text: str) -> str:
        reply_text = truncate_text(reply_text)
        
        if not username or not message_id or not reply_text:
            logger.error("Ошибка: Не указаны обязательные параметры (username, message_id или reply_text).")
            return "Ошибка: Не указаны обязательные параметры (username, message_id или reply_text)."
    
        text = f"@{username} {reply_text}"
        return self.mastodon_client.status_post(text, in_reply_to_id=message_id)

    def fetch_notifications(self):
        notifications = self.mastodon_client.notifications()
        filtered_notifications = []
        for notification in notifications:
            filtered_notifications.append({
                    'id': notification['status']['id'],
                    'created_at': notification['created_at'],
                    'content': bs4.BeautifulSoup(notification['status']['content'], 'html.parser').text,
                    "user_id": notification['account']['id'],
                    "username": notification['account']['username']
                })
        return filtered_notifications

    def fetch_timeline(self):
        timeline = self.mastodon_client.timeline_public(limit=50)

        filtered_timeline = []
        for post in timeline:
            if not self.last_timeline_time or (post['created_at'] >= self.last_timeline_time and post['id'] != self.last_timeline_id):
                self.last_timeline_time = post['created_at']
                self.last_timeline_id = post['id']
                filtered_timeline.append({
                    'id': post['id'],
                    'created_at': post['created_at'],
                    'content': bs4.BeautifulSoup(post['content'], 'html.parser').text,
                    "user_id": post['account']['id'],
                    "username": post['account']['username']
                })
        return filtered_timeline

    def fetch_user_profile(self, user_id: int):
        account = self.mastodon_client.account(user_id)
        return account.get('note', 'Нет описания')

    