from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Choice:
    key: str
    text: str
    is_correct: bool
    explanation: str


@dataclass
class Case:
    case_id: str
    title: str
    scenario: str
    choices: list[Choice]
    success_summary: str
    failure_summary: str


@dataclass
class GameContent:
    title: str
    intro: str
    cases: list[Case]


def _parse_game_content(raw: dict) -> GameContent:
    cases: list[Case] = []
    for raw_case in raw.get("cases", []):
        choices = [
            Choice(
                key=str(choice["key"]).strip().upper(),
                text=choice["text"],
                is_correct=bool(choice["is_correct"]),
                explanation=choice["explanation"],
            )
            for choice in raw_case["choices"]
        ]
        cases.append(
            Case(
                case_id=raw_case["id"],
                title=raw_case["title"],
                scenario=raw_case["scenario"],
                choices=choices,
                success_summary=raw_case["success_summary"],
                failure_summary=raw_case["failure_summary"],
            )
        )

    return GameContent(title=raw["title"], intro=raw["intro"], cases=cases)


def load_game_content(content_file: Path) -> GameContent:
    with content_file.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return _parse_game_content(raw)


def _prompt_choice(choices: Iterable[Choice]) -> Choice:
    indexed_choices = {choice.key: choice for choice in choices}
    while True:
        selected = input("Choose an action: ").strip().upper()
        if selected in indexed_choices:
            return indexed_choices[selected]
        print("Invalid option. Choose one of: " + ", ".join(indexed_choices))


def play_game(content: GameContent) -> int:
    print(content.title)
    print("=" * len(content.title))
    print(content.intro)
    print()

    score = 0
    for index, case in enumerate(content.cases, start=1):
        print(f"Case {index}: {case.title}")
        print(case.scenario)
        for choice in case.choices:
            print(f"  [{choice.key}] {choice.text}")

        selected = _prompt_choice(case.choices)
        print(selected.explanation)

        if selected.is_correct:
            score += 1
            print(case.success_summary)
        else:
            print(case.failure_summary)
        print()

    print(f"Final score: {score}/{len(content.cases)}")
    if score == len(content.cases):
        print("Outstanding work, Detective. Every AML red flag was resolved.")
    elif score > 0:
        print("Good progress. Review the missed clues and reopen unresolved leads.")
    else:
        print("The criminal network escaped this time. Reassess KYC controls and retry.")

    return score


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Play AML Detective, a text-based AML/KYC financial crime investigation game."
    )
    parser.add_argument(
        "--content-file",
        default="game_content.json",
        type=Path,
        help="Path to the JSON document that defines title, intro, and case requirements.",
    )
    args = parser.parse_args()

    try:
        content = load_game_content(args.content_file)
    except FileNotFoundError:
        print(f"Game content file not found: {args.content_file}")
        return 1
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Game content file is invalid: {exc}")
        return 1

    play_game(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
