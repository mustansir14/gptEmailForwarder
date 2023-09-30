from dataclasses import dataclass, field
from datetime import date
from typing import List

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class ReceiverEmail:
    name: str
    email: str
    header: str


@dataclass_json
@dataclass
class PlotRange:
    start: int
    end: int


@dataclass_json
@dataclass
class Project:
    name: str
    phase: int
    plot_range: PlotRange
    linked_contacts: str
    google_sheet_url: str


@dataclass_json
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
    prompt_project: str
    receiver_emails: List[ReceiverEmail]
    projects: List[Project]
    misc_sheet_url: str


@dataclass
class ProjectItemGSheet:
    date_added: date
    plot_no: int
    item_description: str
    quantity: int
    rate: float
    total: float = field(init=False)

    def __post_init__(self):
        if type(self.rate) == float and type(self.quantity) == int:
            self.total = self.rate * self.quantity
        else:
            self.total = None


@dataclass_json
@dataclass
class EmailDetails:
    company: str
    topic: str
    project_name: str
    project_plot: int
    project_location: str
    item_description: str
    quantity: int
    rate: float
