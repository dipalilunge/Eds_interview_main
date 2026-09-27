from datetime import datetime


class SpeechService:

    def __init__(self):
        self.sessions = {}

    def create_session(self, session_id):

        self.sessions[session_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
            "transcript": "",
            "total_words": 0
        }

    def add_transcript(
        self,
        session_id,
        speaker,
        text
    ):

        if session_id not in self.sessions:
            self.create_session(session_id)

        text = (text or "").strip()

        if not text:
            return

        self.sessions[session_id]["messages"].append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        })

        if self.sessions[session_id]["transcript"]:
            self.sessions[session_id]["transcript"] += "\n"

        self.sessions[session_id]["transcript"] += f"{speaker}: {text}"

        self.sessions[session_id]["total_words"] += len(text.split())

    def get_transcript(self, session_id):

        if session_id not in self.sessions:
            return ""

        return self.sessions[session_id]["transcript"]

    def get_messages(self, session_id):

        if session_id not in self.sessions:
            return []

        return self.sessions[session_id]["messages"]

    def get_statistics(self, session_id):

        if session_id not in self.sessions:

            return {
                "messages": 0,
                "words": 0
            }

        session = self.sessions[session_id]

        return {
            "messages": len(session["messages"]),
            "words": session["total_words"]
        }

    def validate_answer(self, answer):

        answer = (answer or "").strip()

        if len(answer) < 5:
            return False, "Answer is too short."

        if len(answer.split()) < 3:
            return False, "Please answer in complete sentences."

        return True, ""

    def delete_session(self, session_id):

        if session_id in self.sessions:
            del self.sessions[session_id]


speech_service = SpeechService()
