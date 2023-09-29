import email
import imaplib
import json
import logging
import smtplib
import ssl
import time
from email import policy
from email.message import EmailMessage, Message
from typing import Iterator, List, Tuple

import openai

from internal.data_types import Configuration, ReceiverEmail
from internal.db import get_config_from_db
from internal.utils import *
from internal.chatgpt import ChatGPT

logging.basicConfig(
    format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %H:%M:%S", level=logging.INFO
)


class EmailForwarder:
    def run_process(self) -> None:
        """
        Runs a single iteration to check for new emails and forward
        """

        self.load_config()

        for email_msg in self.get_new_emails():
            email_details = self.process_email(email_msg)
            topic = self.forward_email(email_details, email_msg)
            # if topic in ["order", "variation"]:
            #     self.add_to_sheet()

    def process_email(self, email_msg: Message) -> EmailDetails:
        """
        Processes and extracts details from email using chatgpt
        """
        email_message, _ = self.construct_email_msg_for_chatgpt(email_msg)
        return self.chatgpt.get_email_details(
            email_message, self.config.prompt_subject_line
        )

    def forward_email(self, email_details: EmailDetails, email_msg: Message) -> str:
        """
        Forwards the email to the appropriate reciever based on topic. Returns topic for further processing
        """

        subject_line = create_subject_line(email_details)
        logging.info(f"Got subject line from chatgpt {subject_line}")
        email_message, body = self.construct_email_msg_for_chatgpt(email_msg)
        reciever_email, topic = self.chatgpt.get_email_and_topic_to_forward_to(
            email_message,
            self.config.receiver_emails,
            self.config.prompt_forward_email,
        )
        new_subject_line = subject_line + " " + email_msg["Subject"]
        self.send_email(reciever_email, new_subject_line, body)
        return topic

    def construct_email_msg_for_chatgpt(self, email_msg: Message) -> Tuple[str, str]:
        email_message = "From: %s\nTo: %s\nDate: %s\nSubject: %s\n\n" % (
            str(email_msg["From"]),
            str(email_msg["To"]),
            str(email_msg["Date"]),
            str(email_msg["Subject"]),
        )

        body = get_body_from_email_msg(email_msg)
        email_message += body
        return email_message, body

    def load_config(self) -> None:
        """
        Loads the configuration JSON from DB
        """
        config = get_config_from_db()
        if not config:
            raise Exception("Config not set!")
        config_json = config.config_json
        self.config: Configuration = Configuration.from_dict(config_json)
        self.chatgpt = ChatGPT(self.config.openai_api_key)

    def get_new_emails(self) -> Iterator[Message]:
        """
        An iterator to login to IMAP, yield new emails and logout
        """
        logging.info("Connecting to IMAP")
        mail = imaplib.IMAP4_SSL(
            self.config.imap_host, int(self.config.imap_port))
        rc, resp = mail.login(self.config.email, self.config.password)
        mail.select("Inbox")
        logging.info("Checking for messages")
        status, data = mail.search(None, "(UNSEEN)")

        for num in data[0].split():
            logging.info("Found new email")
            status, data = mail.fetch(num, "(RFC822)")
            email_msg = data[0][1]
            yield email.message_from_bytes(email_msg, policy=policy.SMTP)

        logging.info("Logging out")
        mail.logout()

    def run_loop(self) -> None:
        """
        Runs the Email Forwarding process in a loop
        """

        while True:
            self.run_process()
            time.sleep(5)

    def send_email(self, reciever_email: str, subject: str, body: str) -> None:
        """
        Send email to given reciever
        """
        em = EmailMessage()
        em.set_content(body)
        em["To"] = reciever_email
        em["From"] = self.config.email
        em["Subject"] = subject
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            self.config.smtp_server, int(self.config.smtp_port), context=context
        ) as server:
            logging.info(f"Forwarding email to {reciever_email}")
            server.login(self.config.email, self.config.password)
            server.send_message(em)


if __name__ == "__main__":
    email_forwarder = EmailForwarder()
    email_forwarder.run_loop()
