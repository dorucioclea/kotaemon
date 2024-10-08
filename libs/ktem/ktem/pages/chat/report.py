import json
import os
from typing import Optional

import gradio as gr
import requests
from ktem.app import BasePage
from ktem.db.models import IssueReport, engine
from sqlmodel import Session


class ReportIssue(BasePage):
    def __init__(self, app):
        self.knet_endpoint = (
            os.environ.get("KN_ENDPOINT", "http://127.0.0.1:8081") + "/feedback"
        )

        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="Feedback", open=False):
            self.correctness = gr.Radio(
                choices=[
                    ("The answer is correct", "correct"),
                    ("The answer is incorrect", "incorrect"),
                ],
                label="Correctness:",
            )
            self.issues = gr.CheckboxGroup(
                choices=[
                    ("The answer is offensive", "offensive"),
                    ("The evidence is incorrect", "wrong-evidence"),
                ],
                label="Other issue:",
            )
            self.more_detail = gr.Textbox(
                placeholder=(
                    "More detail (e.g. how wrong is it, what is the "
                    "correct answer, etc...)"
                ),
                container=False,
                lines=3,
            )
            gr.Markdown(
                "This will send the current chat and the user settings to "
                "help with investigation"
            )
            self.report_btn = gr.Button("Report")

    def report(
        self,
        correctness: str,
        issues: list[str],
        more_detail: str,
        conv_id: str,
        chat_history: list,
        settings: dict,
        user_id: Optional[int],
        info_panel: str,
        chat_state: dict,
        *selecteds,
    ):
        selecteds_ = {}
        for index in self._app.index_manager.indices:
            if index.selector is not None:
                if isinstance(index.selector, int):
                    selecteds_[str(index.id)] = selecteds[index.selector]
                elif isinstance(index.selector, tuple):
                    selecteds_[str(index.id)] = [selecteds[_] for _ in index.selector]
                else:
                    print(f"Unknown selector type: {index.selector}")

        issue_dict = {
            "correctness": correctness,
            "issues": issues,
            "more_detail": more_detail,
        }
        with Session(engine) as session:
            issue = IssueReport(
                issues=issue_dict,
                chat={
                    "conv_id": conv_id,
                    "chat_history": chat_history,
                    "info_panel": info_panel,
                    "chat_state": chat_state,
                    "selecteds": selecteds_,
                },
                settings=settings,
                user=user_id,
            )
            session.add(issue)
            session.commit()

        # forward feedback to KNet service
        try:
            data = {
                "feedback": json.dumps(issue_dict),
                "conv_id": conv_id,
            }
            print(data)
            response = requests.post(self.knet_endpoint, data=data)
            response.raise_for_status()
            print(response.text)
        except Exception as e:
            print("Error submitting Knet feedback:", e)

        gr.Info("Thank you for your feedback")