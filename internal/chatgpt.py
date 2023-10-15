from typing import List, Tuple

import openai

from internal.data_types import EmailDetails, Project, ProjectType, ReceiverEmail
from internal.utils import (get_reciever_email_by_name, get_project_based_on_details,
                            is_prompt_long, remove_middle_words)


class ChatGPT:
    def __init__(self, api_key: str) -> None:
        openai.api_key = api_key

    def request(self, prompt: str) -> str:
        """
        Make a request to chatgpt with given prompt
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        return response.choices[0].message["content"]

    def get_email_details(self, email_message: str, prompt: str, project_types: List[ProjectType]) -> EmailDetails:
        """
        Request chatgpt to extract email details for the given email message
        """
        project_type_dict = {}
        for project_type in project_types:
            project_type_dict[project_type.name] = {
                "hourly_rate": project_type.hour_rate,
                "day_rate": project_type.day_rate,
                "keywords": project_type.keywords
            }
        while True:
            prompt = prompt.replace("{email_message}", email_message).replace(
                "{windows_hourly_rate}", str(project_type_dict["Windows"]["hourly_rate"])).replace(
                "{windows_day_rate}", str(project_type_dict["Windows"]["day_rate"])).replace(
                "{carpentry_hourly_rate}", str(project_type_dict["Carpentry"]["hourly_rate"])).replace(
                "{carpentry_day_rate}", str(project_type_dict["Carpentry"]["day_rate"])).replace(
                "{windows_keywords}", project_type_dict["Windows"]["keywords"]).replace(
                "{carpentry_keywords}", project_type_dict["Carpentry"]["keywords"])
            if is_prompt_long(prompt):
                email_message = remove_middle_words(email_message)
            else:
                return EmailDetails.from_json(self.request(prompt))

    def get_reciever_email_and_topic_to_forward_to(
        self, email_message: str, topic_emails: List[ReceiverEmail], prompt: str
    ) -> Tuple[ReceiverEmail, str]:
        """
        Request chatgpt to find matching topic and email to forward to for the given email message
        """
        topics = "\n".join(topic_email.name for topic_email in topic_emails)
        while True:
            prompt = prompt.replace("{topics}", topics).replace(
                "{email_message}", email_message
            )
            if is_prompt_long(prompt):
                email_message = remove_middle_words(email_message)
            else:
                topic = self.request(prompt)
                return get_reciever_email_by_name(topic_emails, topic), topic

    def get_project_to_add_to(
        self,
        email_message_text: str,
        email_details: EmailDetails,
        projects: List[Project],
        prompt: str,
    ) -> Project | None:
        """
        Request chatgpt to get matching project and its corresponding sheet url for the given email message. Will return None if no matching project
        """

        project_names = "\n".join([project.name for project in projects])
        while True:
            prompt = prompt.replace("{projects}", project_names).replace(
                "{email_message}", email_message_text
            )
            if is_prompt_long(prompt):
                email_message = remove_middle_words(email_message)
            else:
                project = self.request(prompt)
                plot = None
                if email_details.items:
                    plot = email_details.items[0].plot_no
                return get_project_based_on_details(
                    projects, project, plot, email_message_text
                )
