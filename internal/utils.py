import logging
from email.message import Message, EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Tuple

from internal.data_types import EmailDetails, PlotRange, Project, ReceiverEmail


def is_prompt_long(prompt: str) -> bool:
    return len(prompt.split(" ")) > 1500


def get_reciever_email_by_name(topic_emails: List[ReceiverEmail], name: str) -> ReceiverEmail:
    for topic_email in topic_emails:
        if topic_email.name == name:
            return topic_email


def get_project_sheet_url(
    projects: List[Project], name: str, plot: int, email_msg: str
) -> Tuple[str | None, str | None]:
    """
    Returns project sheet url and name based on email details. First match is done by project name and plot, if none matched, then match by contacts and plot
    """
    # search by name and plot
    for project in projects:
        if project.name == name and check_if_plot_matches(plot, project.plot_range):
            return project.google_sheet_url, project.name

    # search by contacts and plot
    for project in projects:
        linked_contacts = [
            contact.strip() for contact in project.linked_contacts.split(",")
        ]

        contacts_found = 0
        for contact in linked_contacts:
            if contact in email_msg:
                contacts_found += 1
                if contacts_found == 2:
                    break

        if contacts_found == 2 and check_if_plot_matches(plot, project.plot_range):
            return project.google_sheet_url, project.name

    return None, None


def check_if_plot_matches(plot: int, plot_range: PlotRange) -> bool:
    if not plot:
        return True
    if plot_range and plot_range.start is not None:
        if plot_range.start <= plot and plot_range.end >= plot:
            return True
    return False


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
        if part.get_content_type() == "text/plain" or part.get_content_type() == "text/html":
            body += part.get_content() + "\n"
    return body


def append_html_at_start_of_email(html_to_append: str, existing_email: EmailMessage) -> EmailMessage:

    html_part = MIMEText(html_to_append, 'html')
    existing_email.attach(html_part)
    return existing_email
