import logging
import json
import time
import imaplib
import email
from email import policy
import openai
import smtplib
import ssl
from email.message import EmailMessage
from db import get_config

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)


def request_chat_gpt(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message["content"]


def get_email_response_from_chatgpt(email_message: str) -> dict:
    while True:
        prompt = f'Consider the email delimited by triple backticks. This email is sent to my construction company. I need as much information identified within this email, comprising of small snippets of descriptive information that will be appended (at the start) of the email subject (when it is forwarded), delimited by **. The information I am looking for (where possible) is "company sending the email", "email topic", "site/project name", "site/project plot number", "site/project location". Return your response in JSON format, with keys "company", "topic", "project_name", "project_plot", "project_location". Your output should only contain the JSON, nothing else. ```\n{email_message}\n```'
        if len(prompt.split(" ")) > 1500:
            logging.info(
                "Prompt contains more than 4097 tokens, chopping off email from the middle")
            email_message = remove_middle_words(email_message)
        else:
            return json.loads(request_chat_gpt(prompt))


def get_email_to_forward_to(email_message: str, topic_emails: dict) -> str:
    topics = "\n".join(list(topic_emails.keys()))
    prompt = f'Consider the email delimited by triple backticks. Determine which of these topics:\n\n{topics}\n\n does the email belong to. Your response should only contain the topic name, nothing else.\n```{email_message}\n```'
    topic = request_chat_gpt(prompt)
    return topic_emails[topic]


def create_subject_line(response: dict) -> str:

    return f"***{response['topic']}*** - {response['company']} - {response['project_name']} - {response['project_plot']} -"


def remove_middle_words(text):
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
    del words[start:end + 1]

    # Reconstruct the text with remaining words
    result_text = ' '.join(words)

    return result_text


if __name__ == "__main__":

    while True:
        config = get_config()
        if not config:
            raise Exception("Config not set!")
        config_json = config.config_json
        openai.api_key = config_json["openai_api_key"]
        imap_host = config_json["imap_host"]
        imap_port = config_json["imap_port"]
        imap_user = config_json["email"]
        imap_pass = config_json["password"]
        smtp_server = config_json["smtp_server"]
        port = config_json["smtp_port"]
        sender_email = imap_user
        password = imap_pass
        topics_emails = config_json['receiver_emails']

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
            reciever_email = get_email_to_forward_to(
                email_message, topics_emails)
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
