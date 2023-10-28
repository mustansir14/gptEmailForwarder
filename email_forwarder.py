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
            logging.info("Email processing done.")

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
                              linked_contacts=None, google_sheet_url_windows=self.config.misc_sheet_url, google_sheet_url_carpentry=None)
        if not project.google_sheet_url_windows and not project.google_sheet_url_carpentry:
            logging.error(
                "No matching project and misc sheet url not set. Can't add project item to gsheet."
            )
            return
        logging.info(f"Project matched: {project.name}")
        email_details.project_name = project.name

        available_gsheet, gsheet_windows, gsheet_carpentry = self.get_google_sheets_for_project(
            project)
        if available_gsheet == None:
            return project, []
        project_items = []
        for item in email_details.items:
            project_item = ProjectItemGSheet(
                date_added=date.today(),
                plot_no=item.plot_no,
                item_description=item.item_description,
                quantity=item.quantity,
                no_of_days_or_hours=item.no_of_days_or_hours,
                rate=item.rate,
                item_type=item.item_type
            )
            if item.item_type == "windows" and gsheet_windows:
                gsheet_windows.insert_project_item(project_item)
            elif item.item_type == "carpentry" and gsheet_carpentry:
                gsheet_carpentry.insert_project_item(project_item)
            else:
                available_gsheet.insert_project_item(project_item)
            logging.info(
                f"Added project item with description {project_item.item_description} to gsheet for project {project.name}"
            )
            project_items.append(project_item)
        return project, project_items

    def add_gdrive_url_to_sheet(self, gdrive_url: str, project: Project, project_items: List[ProjectItemGSheet]) -> None:
        available_gsheet, gsheet_windows, gsheet_carpentry = self.get_google_sheets_for_project(
            project)
        for project_item in project_items:
            try:
                if project_item.item_type == "windows" and gsheet_windows:
                    gsheet_windows.insert_gdrive_link(gdrive_url, project_item)
                elif project_item.item_type == "carpentry" and gsheet_carpentry:
                    gsheet_carpentry.insert_gdrive_link(
                        gdrive_url, project_item)
                else:
                    available_gsheet.insert_gdrive_link(
                        gdrive_url, project_item)
            except ValueError:
                logging.error(
                    f"Error insert gdrive url for project item {project_item.item_ref}. Item does not exist")

    def get_google_sheets_for_project(self, project: Project) -> Tuple[GoogleSheet, GoogleSheet, GoogleSheet]:
        gsheet_windows = None
        gsheet_carpentry = None
        try:
            if project.google_sheet_url_windows is not None and project.google_sheet_url_windows.strip() != "":
                gsheet_windows = GoogleSheet(project.google_sheet_url_windows)
            if project.google_sheet_url_carpentry is not None and project.google_sheet_url_carpentry.strip() != "":
                gsheet_carpentry = GoogleSheet(
                    project.google_sheet_url_carpentry)
        except PermissionError:
            logging.error(
                f"Permission error accessing Gsheet for project {project.name}. Can't add project item"
            )

        if gsheet_windows is None and gsheet_carpentry is None:
            logging.error("No Gsheet URL set, skipping writing to gsheet")
            return None, None, None
        if gsheet_windows is not None:
            available_gsheet = gsheet_windows
        else:
            available_gsheet = gsheet_carpentry
        return available_gsheet, gsheet_windows, gsheet_carpentry

    def process_email(self, email_msg_text: str) -> EmailDetails:
        """
        Processes and extracts details from email using chatgpt
        """
        logging.info("Getting email details from chatgpt")
        email_details = self.chatgpt.get_email_details(
            email_msg_text, self.config.prompt_subject_line, self.config.project_types
        )
        project_type_dict = create_project_type_dict(self.config.project_types)
        for item in email_details.items:
            if item.item_type and item.unit_time:
                if item.unit_time == "day":
                    item.rate = project_type_dict[item.item_type]["day_rate"]
                else:
                    item.rate = project_type_dict[item.item_type]["hourly_rate"]

        return email_details

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
        mail = imaplib.IMAP4_SSL(
            self.config.imap_host, int(self.config.imap_port))
        rc, resp = mail.login(self.config.email, self.config.password)
        mail.select("Inbox")
        status, data = mail.search(None, "(UNSEEN)")

        for num in data[0].split():
            logging.info("Found new email")
            status, data = mail.fetch(num, "(RFC822)")
            email_msg = data[0][1]
            yield email.message_from_bytes(email_msg, policy=policy.SMTP)

        mail.logout()

    def run_loop(self) -> None:
        """
        Runs the Email Forwarding process in a loop
        """

        self.load_config()
        logging.info(f"Logged in as {self.config.email}")
        logging.info("Listening for new emails...")
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
