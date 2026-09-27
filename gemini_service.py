import json
import os

import requests


class GeminiService:
    def __init__(self):
        self.api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.model = (os.getenv("GEMINI_MODEL") or "gemini-2.0-flash").strip()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _normalize_model(self, model_name=None):
        name = (model_name or self.model or "gemini-2.0-flash").strip()
        if not name.startswith("models/"):
            return f"models/{name}"
        return name

    def _candidate_models(self):
        configured = (self.model or "gemini-2.0-flash").strip()
        candidates = [configured]
        for fallback in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"):
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates

    def _extract_text(self, data):
        if not isinstance(data, dict):
            return ""

        candidates = data.get("candidates")
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                content = candidate.get("content")
                if isinstance(content, dict):
                    parts = content.get("parts")
                    if isinstance(parts, list):
                        texts = []
                        for part in parts:
                            if isinstance(part, dict) and part.get("text"):
                                texts.append(str(part.get("text")))
                        if texts:
                            return "\n".join(texts).strip()
                    if content.get("text"):
                        return str(content.get("text")).strip()
                if candidate.get("text"):
                    return str(candidate.get("text")).strip()

        output = data.get("output")
        if isinstance(output, dict):
            if output.get("text"):
                return str(output.get("text")).strip()
            contents = output.get("contents", [])
            if isinstance(contents, list):
                parts = []
                for item in contents:
                    if isinstance(item, dict):
                        text = item.get("text") or item.get("content")
                        if text:
                            parts.append(str(text))
                if parts:
                    return "\n".join(parts).strip()

        for key in ("response", "content"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def _call_gemini(self, prompt, max_tokens=500, temperature=0.7):
        if not self.api_key:
            return ""

        for model_name in self._candidate_models():
            for endpoint in (":generateContent", ":generateText"):
                url = f"{self.base_url}/{self._normalize_model(model_name)}{endpoint}"
                body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    },
                }
                if endpoint == ":generateText":
                    body = {
                        "prompt": {"text": prompt},
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    }

                try:
                    response = requests.post(url, params={"key": self.api_key}, json=body, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    text = self._extract_text(data)
                    if text:
                        self.model = model_name
                        return text
                    fallback_text = response.text.strip()
                    if fallback_text:
                        self.model = model_name
                        return fallback_text
                except Exception:
                    continue

        return ""

    def _parse_json_response(self, text):
        clean_text = (text or "").strip()
        if not clean_text:
            return None
        if clean_text.startswith("```"):
            clean_text = clean_text.strip("`").strip()
            if clean_text.lower().startswith("json"):
                clean_text = clean_text[4:].strip()
        try:
            return json.loads(clean_text)
        except Exception:
            return None

    def _fallback_questions(self, role, level, count):
        base = [
            "Tell me about a recent project you worked on.",
            "Explain a technical challenge you faced and how you solved it.",
            "How do you approach debugging a difficult issue?",
            "Describe a time you worked in a team — what was your role?",
            "What are your learning goals for the next year?",
        ]
        if "mechanical" in (role or "").lower() or "cad" in (role or "").lower():
            base[0] = "Describe a mechanical design project you completed and the tools you used."
            base[1] = "Explain how you validated a design and handled tolerance/fit issues."
        if (level or "").lower() in ("senior", "lead"):
            base.append("How do you mentor junior engineers and conduct design reviews?")
        return base[:count]

    def generate_questions(self, role, level, count=5, resume_text=""):
        prompt = f"""
You are an expert technical interviewer.

Role:
{role}

Candidate Level:
{level}

Resume:
{resume_text}

Generate exactly {count} interview questions.

Rules:
- Mix technical and HR questions.
- Ask resume-based questions when possible.
- Increase difficulty gradually.
- Return ONLY JSON.

Example:
[
    {{
        "id": 1,
        "type": "technical",
        "question": "Explain REST API."
    }}
]
"""

        text = self._call_gemini(prompt, max_tokens=600, temperature=0.6)
        if not text:
            return [
                {"id": idx + 1, "type": "general", "question": question}
                for idx, question in enumerate(self._fallback_questions(role, level, count))
            ]

        parsed = self._parse_json_response(text)
        if isinstance(parsed, list):
            return parsed[:count]

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        questions = []
        for line in lines:
            if line.startswith("[") or line.startswith("]") or line.startswith("{"):
                continue
            if line:
                questions.append({
                    "id": len(questions) + 1,
                    "type": "general",
                    "question": line,
                })
        return questions[:count] or [
            {"id": idx + 1, "type": "general", "question": question}
            for idx, question in enumerate(self._fallback_questions(role, level, count))
        ]

    def evaluate_answer(self, question, answer):
        prompt = f"""
You are an interview evaluator.

Question:

{question}

Answer:

{answer}

Evaluate using JSON.

{{
"score":0-10,
"technical":0-10,
"communication":0-10,
"confidence":0-10,
"feedback":"",
"ideal_answer":"",
"followup":""
}}

Return ONLY JSON.
"""

        text = self._call_gemini(prompt, max_tokens=600, temperature=0.7)
        parsed = self._parse_json_response(text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "score": 0,
            "technical": 0,
            "communication": 0,
            "confidence": 0,
            "feedback": "Unable to evaluate right now.",
            "ideal_answer": "",
            "followup": "",
        }

    def generate_report(self, interview_data):
        prompt = f"""
Create a professional interview report.

Interview Data:

{json.dumps(interview_data)}

Return JSON.

{{
"overall_score":90,
"technical":88,
"communication":91,
"confidence":87,
"strengths":[],
"weaknesses":[],
"recommendations":[]
}}
"""

        text = self._call_gemini(prompt, max_tokens=800, temperature=0.7)
        parsed = self._parse_json_response(text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "overall_score": 0,
            "technical": 0,
            "communication": 0,
            "confidence": 0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }


gemini = GeminiService()
