import logging
from email.message import Message
from typing import List


from internal.data_types import ReceiverEmail, EmailDetails, Project


def is_prompt_long(prompt: str) -> bool:
    return len(prompt.split(" ")) > 1500


def get_email_by_name(topic_emails: List[ReceiverEmail], name: str):
    for topic_email in topic_emails:
        if topic_email.name == name:
            return topic_email.email


def get_project_sheet_url_by_name(projects: List[Project], name: str):
    for project in projects:
        if project.name == name:
            return project.google_sheet_url


def create_subject_line(email_details: EmailDetails) -> str:
    return f"***{email_details.topic}*** - {email_details.company} - {email_details.project_name} - {email_details.project_plot} - {email_details.project_location} - "


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
    del words[start: end + 1]
    # Reconstruct the text with remaining words
    result_text = " ".join(words)
    return result_text


def get_body_from_email_msg(email_msg: Message) -> str:
    body = ""
    for part in email_msg.walk():
        if part.get_content_type() == "text/plain":
            body += part.get_content() + "\n"
    return body
