from unittest import TestCase
import pickle
from internal.utils import prepend_text_to_email


class TestEmailForwarder(TestCase):
    def setUp(self) -> None:
        with open("tests/email.pkl", "rb") as f:
            self.email_message = pickle.load(f)

    def test_prepend_text_to_email(self):

        new_email_message = prepend_text_to_email(
            "New text", self.email_message)

        print(new_email_message)
        assert "New text" in str(new_email_message)
