import email
import imaplib
import logging
import smtplib
import ssl
import time
from datetime import date
from email import policy
from email.message import EmailMessage, Message
from typing import Iterator, Tuple

from internal.chatgpt import ChatGPT
from internal.data_types import Configuration, ProjectItemGSheet
from internal.db import get_config_from_db
from internal.gsheet import GoogleSheet
from internal.utils import *
from internal.gdrive import GoogleDrive

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
            email_msg_text, body = self.construct_email_msg_for_chatgpt(
                email_msg)
            email_details = self.process_email(email_msg_text)
            reciever_email, topic = self.chatgpt.get_reciever_email_and_topic_to_forward_to(
                email_msg_text,
                self.config.receiver_emails,
                self.config.prompt_forward_email,
            )
            if topic in ["order", "variation"]:
                project, project_items = self.add_to_sheet(
                    email_msg_text, email_details)
                gdrive_url = self.add_to_drive(
                    email_msg, project_items, project)
                self.add_gdrive_url_to_sheet(
                    gdrive_url, project, project_items)
            self.forward_email(
                reciever_email, email_details, email_msg
            )

    def add_to_drive(self, email_message: EmailMessage, project_items: List[ProjectItemGSheet], project: Project) -> str:
        logging.info("Saving email and it's attachements to google drive")
        gdrive = GoogleDrive()
        return gdrive.add_email(email_message, project_items, project)

    def add_to_sheet(
        self, email_message_text: str, email_details: EmailDetails
    ) -> Tuple[Project, List[ProjectItemGSheet]]:
        logging.info(
            "Finding project based on name, plot and/or linked contacts")
        project = self.chatgpt.get_project_to_add_to(
            email_message_text,
            email_details,
            self.config.projects,
            self.config.prompt_project,
        )
        if project is None:
            project = Project(name="Misc", phase=None, plot_range=None,
                              linked_contacts=None, google_sheet_url=self.config.misc_sheet_url)
        if not project.google_sheet_url:
            logging.error(
                "No matching project and misc sheet url not set. Can't add project item to gsheet."
            )
            return
        logging.info(f"Project matched: {project.name}")
        email_details.project_name = project.name
        try:
            gsheet = GoogleSheet(project.google_sheet_url)
        except PermissionError:
            logging.error(
                f"Permission error accessing Gsheet for project {project.name}. Can't add project item"
            )
            return
        project_items = []
        for item in email_details.items:
            project_item = ProjectItemGSheet(
                date_added=date.today(),
                plot_no=email_details.project_plot,
                item_description=item.item_description,
                quantity=item.quantity,
                rate=item.rate,
            )
            gsheet.insert_project_item(project_item)
            logging.info(
                f"Added project item with description {project_item.item_description} to gsheet for project {project.name}"
            )
            project_items.append(project_item)
        return project, project_items

    def add_gdrive_url_to_sheet(self, gdrive_url: str, project: Project, project_items: List[ProjectItemGSheet]) -> None:
        try:
            gsheet = GoogleSheet(project.google_sheet_url)
        except PermissionError:
            logging.error(
                f"Permission error accessing Gsheet for project {project.name}. Can't insert gdrive url"
            )
            return
        for project_item in project_items:
            try:
                gsheet.insert_gdrive_link(gdrive_url, project_item)
            except ValueError:
                logging.error(
                    f"Error insert gdrive url for project item {project_item.item_ref}. Item does not exist")

    def process_email(self, email_msg_text: str) -> EmailDetails:
        """
        Processes and extracts details from email using chatgpt
        """
        logging.info("Getting email details from chatgpt")
        return self.chatgpt.get_email_details(
            email_msg_text, self.config.prompt_subject_line
        )

    def forward_email(
        self, reciever_email: ReceiverEmail, email_details: EmailDetails, email_message: EmailMessage
    ) -> None:
        """
        Forwards the email to the given reciever. Modifies subject based on email details.
        """

        subject_line = create_subject_line(email_details)
        logging.info(f"Got subject line from chatgpt {subject_line}")

        new_subject = subject_line + \
            " " + email_message["Subject"]
        del email_message["Subject"]
        email_message["Subject"] = new_subject
        del email_message["To"]
        del email_message["From"]
        email_message["To"] = reciever_email.email
        email_message["From"] = self.config.email
        if reciever_email.header:
            email_message = append_html_at_start_of_email(
                reciever_email.header, email_message)
        self.send_email(email_message)

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

    def send_email(self, email_message: Message) -> None:
        """
        Send email to given reciever
        """

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            self.config.smtp_server, int(self.config.smtp_port), context=context
        ) as server:
            logging.info(f"Forwarding email to {email_message['To']}")
            server.login(self.config.email, self.config.password)
            server.send_message(email_message)


if __name__ == "__main__":
    email_forwarder = EmailForwarder()
    email_forwarder.run_loop()
