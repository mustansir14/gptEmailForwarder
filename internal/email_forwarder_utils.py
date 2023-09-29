import json
import logging
from email.message import Message
from typing import List, Tuple

import openai

from internal.data_types import ReceiverEmail


def request_chat_gpt(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message["content"]


def is_prompt_long(prompt: str) -> bool:
    return len(prompt.split(" ")) > 1500


def get_subject_line_from_chatgpt(email_message: str, prompt: str) -> dict:
    while True:
        prompt = prompt.replace("{email_message}", email_message)
        if is_prompt_long(prompt):
            email_message = remove_middle_words(email_message)
        else:
            res = json.loads(request_chat_gpt(prompt))
            return create_subject_line(res)


def get_email_and_topic_to_forward_to(
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
            topic = request_chat_gpt(prompt)
            return get_email_by_name(topic_emails, topic), topic


def get_email_by_name(topic_emails: List[ReceiverEmail], name: str):
    for topic_email in topic_emails:
        if topic_email.name == name:
            return topic_email.email


def create_subject_line(response: dict) -> str:
    return f"***{response['topic']}*** - {response['company']} - {response['project_name']} - {response['project_plot']} -"


def remove_middle_words(text):
    logging.info(
        "Prompt contains more than 4097 tokens, chopping off email from the middle"
    )
    # Split the text into words using whitespace as the delimiter
    words = text.split(" ")
    # Calculate the number of words to remove (1/4th of the total words)
    n = len(words)
    k = n // 4
    # Calculate the start and end values for the middle range
    start = (n - k) // 2 + 1
    end = start + k - 1
    # Check if the range is valid
    if start < 1:
        start = 1
        end = k
    if end > n:
        end = n
    # Remove the middle portion of words
    del words[start : end + 1]
    # Reconstruct the text with remaining words
    result_text = " ".join(words)
    return result_text


def get_body_from_email_msg(email_msg: Message) -> str:
    body = ""
    for part in email_msg.walk():
        if part.get_content_type() == "text/plain":
            body += part.get_content() + "\n"
    return body
