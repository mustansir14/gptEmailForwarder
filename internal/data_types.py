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
    phase: int | None
    plot_range: PlotRange | None
    linked_contacts: str | None
    google_sheet_url_windows: str | None
    google_sheet_url_carpentry: str | None


@dataclass_json
@dataclass
class ProjectType:
    name: str
    day_rate: float
    hour_rate: float
    keywords: str


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
    project_types: List[ProjectType]


@dataclass
class ProjectItemGSheet:
    item_ref: int = field(init=False)
    date_added: date
    plot_no: int
    item_description: str
    quantity: int
    rate: float
    no_of_days_or_hours: int
    total: float = field(init=False)
    item_type: str | None

    def __post_init__(self):
        self.total = None
        if self.rate is None:
            return
        if self.quantity is not None:
            self.total = self.rate * self.quantity
        if self.no_of_days_or_hours is not None:
            if self.total is None:
                self.total = self.rate
            self.total = self.total * self.no_of_days_or_hours

    def get_combined_quantity(self) -> str | None:
        if self.quantity and self.no_of_days_or_hours:
            return f"{self.quantity}x{self.no_of_days_or_hours}"
        if self.quantity:
            return str(self.quantity)
        if self.no_of_days_or_hours:
            return str(self.no_of_days_or_hours)
        return None


@dataclass_json
@dataclass
class EmailItem:
    item_description: str
    plot_no: int | None
    quantity: int | None
    rate: float | None
    item_type: str
    no_of_days_or_hours: int | None
    unit_time: str | None


@dataclass_json
@dataclass
class EmailDetails:
    company: str
    topic: str
    project_name: str | None
    project_location: str | None
    items: List[EmailItem]
