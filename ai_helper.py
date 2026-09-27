import os
import requests
import json
try:
    import openai
except Exception:
    openai = None


def _openai_available():
    return openai is not None and bool(os.environ.get("OPENAI_API_KEY"))


def _gemini_available():
    return bool(os.environ.get("GEMINI_API_KEY"))


def _call_gemini(prompt: str, model: str = None, max_tokens: int = 512) -> str:
    """Call Google Generative Language (Gemini) REST API using an API key.
    The app supports both the older generateText endpoint and the newer generateContent payload.
    Returns the generated text or empty string on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ""

    model_name = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"

    base_url = "https://generativelanguage.googleapis.com/v1beta"

    for endpoint in (":generateContent", ":generateText"):
        url = f"{base_url}/{model_name}{endpoint}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": max_tokens},
        }
        if endpoint == ":generateText":
            body = {"prompt": {"text": prompt}, "temperature": 0.7, "maxOutputTokens": max_tokens}

        try:
            resp = requests.post(url, headers={"Content-Type": "application/json"}, params={"key": api_key}, json=body, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                candidates = data.get("candidates")
                if isinstance(candidates, list):
                    for candidate in candidates:
                        if isinstance(candidate, dict):
                            content = candidate.get("content")
                            if isinstance(content, dict):
                                parts = content.get("parts")
                                if isinstance(parts, list):
                                    texts = [part.get("text") for part in parts if isinstance(part, dict) and part.get("text")]
                                    if texts:
                                        return "\n".join(texts).strip()
                                if content.get("text"):
                                    return str(content.get("text")).strip()
                output = data.get("output")
                if isinstance(output, dict):
                    if output.get("text"):
                        return str(output.get("text")).strip()
                    if output.get("contents"):
                        parts = []
                        for c in output.get("contents"):
                            text = c.get("text") or c.get("content")
                            if text:
                                parts.append(str(text))
                        if parts:
                            return "\n".join(parts).strip()
            if resp.text.strip():
                return resp.text.strip()
        except Exception:
            continue

    return ""


def generate_questions(role: str = "candidate", level: str = "junior", count: int = 5):
    role = (role or "candidate").strip()
    level = (level or "junior").strip()

    # Prefer Gemini if configured
    if _gemini_available():
        prompt = (
            f"Generate {count} concise interview questions for a {level} {role} role. "
            "Return the questions as a JSON array only."
        )
        text = _call_gemini(prompt, max_tokens=500)
        if text:
            try:
                q = json.loads(text)
                if isinstance(q, list):
                    return q[:count]
            except Exception:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if lines:
                    return lines[:count]

    # Fallback to OpenAI if available
    if _openai_available():
        try:
            prompt = (
                f"Generate {count} concise interview questions for a {level} {role} role. "
                "Return the questions as a JSON array only."
            )
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            resp = openai.Completion.create(
                engine="text-davinci-003", prompt=prompt, max_tokens=500, temperature=0.7
            )
            text = resp.choices[0].text.strip()
            try:
                q = json.loads(text)
                if isinstance(q, list):
                    return q[:count]
            except Exception:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if lines:
                    return lines[:count]
        except Exception:
            pass

    # Fallback static questions
    base = [
        "Tell me about a recent project you worked on.",
        "Explain a technical challenge you faced and how you solved it.",
        "How do you approach debugging a difficult issue?",
        "Describe a time you worked in a team — what was your role?",
        "What are your learning goals for the next year?",
    ]
    if "mechanical" in role.lower() or "cad" in role.lower():
        base[0] = "Describe a mechanical design project you completed and the tools you used."
        base[1] = "Explain how you validated a design and handled tolerance/fit issues."
    if level.lower() in ("senior", "lead"):
        base.append("How do you mentor junior engineers and conduct design reviews?")
    return base[:count]


def evaluate_answers(questions, answers):
    """Return evaluation list of {question, answer, score, feedback}.
    Prefer Gemini if configured, else OpenAI, else simple heuristics.
    """
    # Prefer Gemini
    if _gemini_available():
        try:
            payload = []
            for q, a in zip(questions, answers):
                payload.append({"question": q, "answer": a})
            prompt = (
                "Evaluate the following interview answers. For each Q/A, give a short (1-2 sentence) feedback and a score 1-5. "
                "Return JSON array of {question, answer, score, feedback}.\n\n" + json.dumps(payload, ensure_ascii=False)
            )
            text = _call_gemini(prompt, max_tokens=800)
            if text:
                try:
                    data = json.loads(text)
                    return data
                except Exception:
                    pass
        except Exception:
            pass

    # OpenAI fallback
    if _openai_available():
        try:
            payload = []
            for q, a in zip(questions, answers):
                payload.append({"question": q, "answer": a})
            prompt = (
                "Evaluate the following interview answers. For each Q/A, give a short (1-2 sentence) feedback and a score 1-5. "
                "Return JSON array of {question, answer, score, feedback}.\n\n" + json.dumps(payload, ensure_ascii=False)
            )
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            resp = openai.Completion.create(
                engine="text-davinci-003", prompt=prompt, max_tokens=800, temperature=0.5
            )
            text = resp.choices[0].text.strip()
            try:
                data = json.loads(text)
                return data
            except Exception:
                pass
        except Exception:
            pass

    # Simple heuristic evaluation
    results = []
    for q, a in zip(questions, answers):
        ans = (a or "").strip()
        score = 1
        feedback = "Answer is too short; add specifics and outcomes."
        if len(ans) > 250:
            score = 5
            feedback = "Strong answer: detailed with outcomes and clear impact."
        elif len(ans) > 120:
            score = 4
            feedback = "Good answer: includes approach and result; could add more metrics."
        elif len(ans) > 60:
            score = 3
            feedback = "Fair answer: basic approach described but needs more detail."
        results.append({"question": q, "answer": a, "score": score, "feedback": feedback})
    return results
