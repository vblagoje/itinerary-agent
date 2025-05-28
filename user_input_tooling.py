from typing import Annotated
import questionary
import re


from haystack.tools import tool


def extract_questions(text: str) -> list[str]:
    """
    Split input string into individual questions.
    Supports numbered or newline-separated formats.
    """
    # Split by numbered format: 1. Question..., 2. Question...
    matches = re.findall(r"\d+\.\s+(.*?)(?=(?:\d+\.\s+)|$)", text, re.DOTALL)
    if matches:
        return [q.strip() for q in matches]

    # Fallback: split by newlines
    return [q.strip() for q in text.strip().split("\n") if q.strip()]


@tool
def human_in_loop_tool(
    question: Annotated[
        str, "One or more clarifying questions separated by newlines or numbers."
    ],
) -> str:
    """Ask one or more questions to the user and return their answers as a combined string."""
    questions = extract_questions(question)

    if len(questions) == 1:
        return questionary.text(f"[Agent] {questions[0]}").ask()

    answers = []
    for q in questions:
        a = questionary.text(q).ask()
        answers.append(f"{q}\n{a}\n")

    return "\n".join(answers).strip()


@tool
def hand_off_to_next_tool(
    objective_and_preferences: Annotated[
        str,
        "Collected objective and preferences to be passed to the next tool as formatted markdown",
    ],
) -> str:
    """
    Collected objective and preferences to be passed to the next tool as formatted markdown
    """
    return objective_and_preferences
