from dataclasses import dataclass
from typing import List


@dataclass
class ReceiverEmail:
    name: str
    email: str


@dataclass
class Configuration:
    imap_host: str
    imap_port: int
    email: str
    password: str
    openai_api_key: str
    smtp_server: str
    smtp_port: int
    prompt_subject_line: str
    prompt_forward_email: str
    receiver_emails: List[ReceiverEmail]
