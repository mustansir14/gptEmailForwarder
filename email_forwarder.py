import email
import imaplib
import json
import logging
import smtplib
import ssl
import time
from email import policy
from email.message import EmailMessage
from typing import List

import openai

from internal.data_types import Configuration, ReceiverEmail
from internal.db import get_config_from_db

logging.basicConfig(
    format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %H:%M:%S", level=logging.INFO
)


class EmailForwarder:
    def load_config(self) -> None:
        config = get_config_from_db()
        if not config:
            raise Exception("Config not set!")
        config_json = config.config_json
        self.config = Configuration(**config_json)
        self.config.receiver_emails = [
            ReceiverEmail(**receiver_email)
            for receiver_email in config_json["receiver_emails"]
        ]
        openai.api_key = self.config.openai_api_key

    def run_process(self) -> None:
        """
        Runs a single iteration to check for new emails and forward
        """

        self.load_config()
        logging.info("Connecting to IMAP")
        # init imap connection
        mail = imaplib.IMAP4_SSL(
            self.config.imap_host, int(self.config.imap_port))
        rc, resp = mail.login(self.config.email, self.config.password)

        # select only unread messages from inbox
        mail.select("Inbox")
        logging.info("Checking for messages")
        status, data = mail.search(None, "(UNSEEN)")

        # for each e-mail messages, print text content
        for num in data[0].split():
            logging.info("Found new email")
            # get a single message and parse it by policy.SMTP (RFC compliant)
            status, data = mail.fetch(num, "(RFC822)")
            email_msg = data[0][1]
            email_msg = email.message_from_bytes(email_msg, policy=policy.SMTP)

            email_message = "From: %s\nTo: %s\nDate: %s\nSubject: %s\n\n" % (
                str(email_msg["From"]),
                str(email_msg["To"]),
                str(email_msg["Date"]),
                str(email_msg["Subject"]),
            )

            # print only message parts that contain text data
            body = ""
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_content() + "\n"

            email_message += body
            res = get_email_response_from_chatgpt(
                email_message, self.config.prompt_subject_line
            )
            subject_line = create_subject_line(res)
            logging.info(f"Got subject line from chatgpt {subject_line}")
            new_subject_line = subject_line + " " + email_msg["Subject"]
            context = ssl.create_default_context()
            reciever_email = get_email_to_forward_to(
                email_message,
                self.config.receiver_emails,
                self.config.prompt_forward_email,
            )
            em = EmailMessage()
            em.set_content(body)
            em["To"] = reciever_email
            em["From"] = self.config.email
            em["Subject"] = new_subject_line
            with smtplib.SMTP_SSL(
                self.config.smtp_server, int(self.config.smtp_port), context=context
            ) as server:
                logging.info(f"Forwarding email to {reciever_email}")
                server.login(self.config.email, self.config.password)
                server.send_message(em)

        logging.info("Logging out")
        mail.logout()

    def run_loop(self) -> None:
        """
        Runs the Email Forwarding process in a loop
        """

        while True:
            self.run_process()
            time.sleep(5)


def request_chat_gpt(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message["content"]


def is_prompt_long(prompt: str) -> bool:
    return len(prompt.split(" ")) > 1500


def get_email_response_from_chatgpt(email_message: str, prompt: str) -> dict:
    while True:
        prompt = prompt.replace("{email_message}", email_message)
        if is_prompt_long(prompt):
            email_message = remove_middle_words(email_message)
        else:
            return json.loads(request_chat_gpt(prompt))


def get_email_to_forward_to(
    email_message: str, topic_emails: List[ReceiverEmail], prompt: str
) -> str:
    topics = "\n".join(topic_email.name for topic_email in topic_emails)
    while True:
        prompt = prompt.replace("{topics}", topics).replace(
            "{email_message}", email_message
        )
        if is_prompt_long(prompt):
            email_message = remove_middle_words(email_message)
        else:
            topic = request_chat_gpt(prompt)
            return get_email_by_name(topic_emails, topic)


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
    del words[start: end + 1]

    # Reconstruct the text with remaining words
    result_text = " ".join(words)

    return result_text


if __name__ == "__main__":
    email_forwarder = EmailForwarder()
    email_forwarder.run_loop()
