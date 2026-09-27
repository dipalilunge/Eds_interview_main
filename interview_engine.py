from dataclasses import dataclass, field
from typing import List, Dict, Optional
from uuid import uuid4
from datetime import datetime

from gemini_service import gemini


@dataclass
class InterviewSession:
    session_id: str
    role: str
    level: str
    questions: List[Dict]
    current_index: int = 0
    answers: List[Dict] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed: bool = False


class InterviewEngine:

    def __init__(self):
        self.sessions = {}

    def create_session(
        self,
        role: str,
        level: str,
        count: int = 5,
        resume_text: str = ""
    ):

        questions = gemini.generate_questions(
            role=role,
            level=level,
            count=count,
            resume_text=resume_text
        )

        session = InterviewSession(
            session_id=str(uuid4()),
            role=role,
            level=level,
            questions=questions
        )

        self.sessions[session.session_id] = session

        return session

    def get_session(self, session_id):

        return self.sessions.get(session_id)

    def get_current_question(self, session_id):

        session = self.get_session(session_id)

        if not session:
            return None

        if session.current_index >= len(session.questions):
            return None

        return session.questions[session.current_index]

    def submit_answer(
        self,
        session_id,
        answer
    ):

        session = self.get_session(session_id)

        if not session:
            return None

        question = session.questions[session.current_index]

        result = gemini.evaluate_answer(
            question["question"],
            answer
        )

        session.answers.append({
            "question": question["question"],
            "answer": answer,
            "evaluation": result
        })

        session.current_index += 1

        if session.current_index >= len(session.questions):
            session.completed = True

        return result

    def next_question(self, session_id):

        session = self.get_session(session_id)

        if not session:
            return None

        if session.completed:
            return None

        return session.questions[session.current_index]

    def interview_completed(self, session_id):

        session = self.get_session(session_id)

        if not session:
            return True

        return session.completed

    def generate_report(self, session_id):

        session = self.get_session(session_id)

        if not session:
            return None

        report = gemini.generate_report(
            {
                "role": session.role,
                "level": session.level,
                "answers": session.answers
            }
        )

        report["questions"] = session.questions
        report["answers"] = session.answers
        report["session_id"] = session.session_id
        report["started_at"] = session.started_at

        return report

    def delete_session(self, session_id):

        if session_id in self.sessions:
            del self.sessions[session_id]


engine = InterviewEngine()
