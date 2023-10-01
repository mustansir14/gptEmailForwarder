from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
import io
from googleapiclient.http import MediaIoBaseUpload
import json
from internal.env import Env
from internal.data_types import ProjectItemGSheet, Project
from email.message import EmailMessage
from internal.utils import get_body_from_email_msg
import mimetypes

MAIN_FOLDER_ID = "1lK9BOZSbmp0D5uPjHlNPD-DBlQ9fsp7v"


class GoogleDrive:

    def __init__(self) -> None:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(Env.GOOGLE_SERVICE_ACCOUNT_KEY_JSON))
        self.service: Resource = build('drive', 'v3', credentials=credentials)

    def add_email(self, email_message: EmailMessage, project_item: ProjectItemGSheet, project: Project) -> None:
        # Extract email subject to use as the subfolder name
        email_subject = email_message['Subject']
        # Create a subfolder with the email subject as its title
        subfolder_metadata = {
            'name': f"{project.name} - {project.phase} - {project_item.item_ref} - {project_item.date_added}",
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [MAIN_FOLDER_ID]
        }
        subfolder = self.service.files().create(
            body=subfolder_metadata,
            fields='id'
        ).execute()

        # Create a MediaIoBaseUpload object for the email HTML content
        # Create a simplified HTML content
        email_html_content = f"""
        <html>
        <head></head>
        <body>
            <p><strong>From:</strong> {email_message['From']}</p>
            <p><strong>To:</strong> {email_message['To']}</p>
            <p><strong>Subject:</strong> {email_message['Subject']}</p>
            <p>{get_body_from_email_msg(email_message)}</p>
        </body>
        </html>
        """
        email_html_media = MediaIoBaseUpload(io.BytesIO(
            email_html_content.encode('utf-8')), mimetype='text/html', resumable=True)

        # Upload the email HTML content to the subfolder
        email_html_metadata = {
            'name': 'email.html',
            'parents': [subfolder['id']]
        }
        self.service.files().create(
            media_body=email_html_media,
            body=email_html_metadata,
            fields='id'
        ).execute()

        # Save email attachments to the subfolder
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            filename = part.get_filename()
            if filename:
                mime_type, _ = mimetypes.guess_type(filename)
                attachment_data = part.get_payload(decode=True)
                media = MediaIoBaseUpload(io.BytesIO(
                    attachment_data), mimetype=mime_type, resumable=True)
                attachment_metadata = {
                    'name': filename,
                    'parents': [subfolder['id']]
                }
                attachment_file = self.service.files().create(
                    media_body=media,
                    body=attachment_metadata,
                    fields='id'
                ).execute()
