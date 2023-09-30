from datetime import date
import json

import gspread

from internal.data_types import ProjectItemGSheet
from internal.env import Env


class GoogleSheet:
    def __init__(self, sheet_url: str) -> None:
        self.gc = gspread.service_account_from_dict(
            json.loads(Env.GOOGLE_SERVICE_ACCOUNT_KEY_JSON))
        self.sh = self.gc.open_by_url(sheet_url)
        self.sheet = self.sh.sheet1

    def insert_project_item(self, project_item: ProjectItemGSheet) -> None:
        first_col_values = self.sheet.col_values(1)
        try:
            new_ref = int(first_col_values[-1]) + 1
        except (ValueError, IndexError):
            new_ref = 1
        new_index = len(first_col_values) + 1
        new_row = [
            new_ref,
            project_item.date_added.strftime("%m/%d/%Y"),
            project_item.plot_no,
            project_item.item_description,
            project_item.quantity,
            project_item.rate,
            project_item.total,
        ]
        self.sheet.insert_row(new_row, new_index)


if __name__ == "__main__":
    gsheet = GoogleSheet(
        "https://docs.google.com/spreadsheets/d/1p-W6vbGU2312a1_T4xyqBWr7Pz8iwmE2EXa68ex690w/edit#gid=638267015",
    )
    gsheet.insert_project_item(
        ProjectItemGSheet(
            date_added=date.today(),
            plot_no=100,
            item_description="Test item",
            quantity=2,
            rate=10.5,
        )
    )
