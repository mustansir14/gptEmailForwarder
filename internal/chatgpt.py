import openai
from internal.data_types import EmailDetails, ReceiverEmail
from internal.utils import is_prompt_long, remove_middle_words, get_email_by_name
from typing import List, Tuple


class ChatGPT:

    def __init__(self, api_key: str) -> None:
        openai.api_key = api_key

    def request(self, prompt: str) -> str:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        return response.choices[0].message["content"]

    def get_email_details(self, email_message: str, prompt: str) -> EmailDetails:
        while True:
            prompt = prompt.replace("{email_message}", email_message)
            if is_prompt_long(prompt):
                email_message = remove_middle_words(email_message)
            else:
                return EmailDetails.from_json(self.request(prompt))

    def get_email_and_topic_to_forward_to(self,
                                          email_message: str, topic_emails: List[ReceiverEmail], prompt: str
                                          ) -> Tuple[str, str]:
        topics = "\n".join(topic_email.name for topic_email in topic_emails)
        while True:
            prompt = prompt.replace("{topics}", topics).replace(
                "{email_message}", email_message
            )
            if is_prompt_long(prompt):
                email_message = remove_middle_words(email_message)
            else:
                topic = self.request(prompt)
                return get_email_by_name(topic_emails, topic), topic
