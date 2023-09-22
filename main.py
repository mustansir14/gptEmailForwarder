import imaplib
import email
from email import policy
import openai
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv
import os
import time
import json
import logging
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def request_chat_gpt(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message["content"]


def get_email_response_from_chatgpt(email_message: str) -> dict:
    prompt = f'Consider the email delimited by triple backticks. This email is sent to my construction company. I need as much information identified within this email, comprising of small snippets of descriptive information that will be appended (at the start) of the email subject (when it is forwarded), delimited by **. The information I am looking for (where possible) is "company sending the email", "email topic", "site/project name", "site/project plot number", "site/project location". Return your response in JSON format, with keys "company", "topic", "project_name", "project_plot", "project_location". Your output should only contain the JSON, nothing else. ```\n{email_message}\n```'
    return json.loads(request_chat_gpt(prompt))


def get_email_to_forward_to(topic: str) -> str:
    prompt = f'Consider the text delimited by triple backticks. Determine which of these topics ["tender", "variation", "order", "advertising", "customer care", "audit", "report", "sales] is the text most similar to. Your response should only contain the topic name, nothing else.'
    topic = request_chat_gpt(prompt)
    return os.getenv(f"RECIEVER_EMAIL_{topic.upper().replace(' ', '_')}")


def create_subject_line(response: dict) -> str:

    return f"***{response['topic']}*** - {response['company']} - {response['project_name']} - {response['project_plot']} -"


if __name__ == "__main__":
    imap_host = os.getenv("IMAP_HOST")
    imap_port = os.getenv("IMAP_PORT")
    imap_user = os.getenv("EMAIL")
    imap_pass = os.getenv("PASSWORD")

    smtp_server = os.getenv("SMTP_SERVER")
    port = os.getenv("SMTP_PORT")  # For starttls
    sender_email = imap_user
    password = imap_pass

    while True:
        logging.info("Connecting to IMAP")
        # init imap connection
        mail = imaplib.IMAP4_SSL(imap_host, int(imap_port))
        rc, resp = mail.login(imap_user, imap_pass)

        # select only unread messages from inbox
        mail.select('Inbox')
        logging.info("Checking for messages")
        status, data = mail.search(None, '(UNSEEN)')

        # for each e-mail messages, print text content
        for num in data[0].split():
            logging.info("Found new email")
            # get a single message and parse it by policy.SMTP (RFC compliant)
            status, data = mail.fetch(num, '(RFC822)')
            email_msg = data[0][1]
            email_msg = email.message_from_bytes(email_msg, policy=policy.SMTP)

            email_message = "From: %s\nTo: %s\nDate: %s\nSubject: %s\n\n" % (
                str(email_msg['From']),
                str(email_msg['To']),
                str(email_msg['Date']),
                str(email_msg['Subject']))

            # print only message parts that contain text data
            body = ""
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_content() + "\n"

            email_message += body
            res = get_email_response_from_chatgpt(email_message)
            subject_line = create_subject_line(res)
            logging.info(f"Got subject line from chatgpt {subject_line}")
            new_subject_line = subject_line + " " + email_msg['Subject']
            context = ssl.create_default_context()
            reciever_email = get_email_to_forward_to(res['topic'])
            em = EmailMessage()
            em.set_content(body)
            em['To'] = reciever_email
            em['From'] = sender_email
            em['Subject'] = new_subject_line
            with smtplib.SMTP_SSL(smtp_server, int(port), context=context) as server:
                logging.info(f"Forwarding email to {reciever_email}")
                server.login(sender_email, password)
                server.send_message(em)

        logging.info("Logging out")
        mail.logout()

        time.sleep(5)
