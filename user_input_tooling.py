from typing import Annotated, List, Union
import questionary
import re
import json5
from haystack.tools import tool

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def strip_code_fence(text: str) -> str:
    """Return inner JSON if wrapped in ```json …``` or plain ``` …```."""
    m = FENCE_RE.search(text)
    return m.group(1) if m else text


def extract_questions(text: str) -> List[str]:
    """Fallback splitter for numbered / newline lists."""
    blocks = re.findall(r"\d+\.\s+(.*?)(?=(?:\d+\.\s+)|$)", text, re.DOTALL)
    if blocks:
        return [b.strip() for b in blocks]
    return [l.strip() for l in text.splitlines() if l.strip()]


def parse_input(text: str) -> List[str]:
    cleaned = strip_code_fence(text.strip())  # remove ```json ``` if present
    try:
        data = json5.loads(cleaned)
        if isinstance(data, dict) and isinstance(data.get("questions"), list):
            return [q.strip() for q in data["questions"] if q.strip()]
    except Exception:
        pass
    return extract_questions(text)


@tool
def human_in_loop_tool(
    questions: Annotated[
        Union[str, dict, list], "JSON string or dict with 'questions' array"
    ],
) -> str:
    """Asks the clarification questions and return input answers from the user as plain text."""
    # Handle different input types
    if isinstance(questions, str):
        questions_list = parse_input(questions)
    elif isinstance(questions, dict):
        questions_list = questions.get("questions", [])
        if not questions_list:
            # If no 'questions' key, treat the dict as a single question
            questions_list = [str(questions)]
    elif isinstance(questions, list):
        questions_list = questions

    if not questions_list:
        raise ValueError(
            f"No questions found in input {questions} of type {type(questions)}"
        )

    answers = [f"{q}\n{questionary.text(q).ask()}\n" for q in questions_list]
    return "".join(answers).strip()


@tool
def hand_off_to_next_tool(
    objective_and_preferences: Annotated[
        str,
        "Collected objective and preferences to be passed to the next tool as formatted markdown",
    ],
) -> str:
    """Stub: simply passes on the gathered info."""
    return objective_and_preferences
