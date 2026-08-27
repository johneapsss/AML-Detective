from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class Evidence:
    evidence_id: str
    description: str
    source: str
    related: str
    reliability: str
    is_red_flag_easy: bool
    connects_to: list[str]
    conditions: str


@dataclass
class Action:
    key: str
    text: str
    costs: dict[str, int]
    reveals_evidence: list[str]
    narrative: str
    risk_indicator: str


@dataclass
class Conclusion:
    key: str
    label: str
    outcome_type: str


@dataclass
class Case:
    case_id: str
    title: str
    difficulty: str
    opening: str
    characters: list[str]
    entities: list[str]
    evidence: list[Evidence]
    actions: list[Action]
    conclusions: list[Conclusion]
    correct_conclusion: str
    actual_activity: str
    key_red_flags: list[str]
    recommended_approach: str


@dataclass
class GameContent:
    title: str
    intro: str
    disclaimer: str
    starting_resources: dict[str, int]
    rank_thresholds: dict[str, int]
    cases: list[Case]


@dataclass
class PlayerProfile:
    experience: int
    capacity: dict[str, int]


def _parse_game_content(raw: dict) -> GameContent:
    cases: list[Case] = []
    for raw_case in raw.get("cases", []):
        evidence = [
            Evidence(
                evidence_id=item["id"],
                description=item["description"],
                source=item["source"],
                related=item["related"],
                reliability=item["reliability"],
                is_red_flag_easy=bool(item["is_red_flag_easy"]),
                connects_to=list(item.get("connects_to", [])),
                conditions=item["conditions"],
            )
            for item in raw_case["evidence"]
        ]
        actions = [
            Action(
                key=str(item["key"]).strip().upper(),
                text=item["text"],
                costs={k: int(v) for k, v in item["costs"].items()},
                reveals_evidence=list(item.get("reveals_evidence", [])),
                narrative=item["narrative"],
                risk_indicator=item["risk_indicator"],
            )
            for item in raw_case["actions"]
        ]
        conclusions = [
            Conclusion(
                key=str(item["key"]).strip().upper(),
                label=item["label"],
                outcome_type=item["outcome_type"],
            )
            for item in raw_case["conclusions"]
        ]
        cases.append(
            Case(
                case_id=raw_case["id"],
                title=raw_case["title"],
                difficulty=raw_case["difficulty"],
                opening=raw_case["opening"],
                characters=list(raw_case["characters"]),
                entities=list(raw_case["entities"]),
                evidence=evidence,
                actions=actions,
                conclusions=conclusions,
                correct_conclusion=str(raw_case["correct_conclusion"]).upper(),
                actual_activity=raw_case["actual_activity"],
                key_red_flags=list(raw_case["key_red_flags"]),
                recommended_approach=raw_case["recommended_approach"],
            )
        )

    return GameContent(
        title=raw["title"],
        intro=raw["intro"],
        disclaimer=raw["disclaimer"],
        starting_resources={k: int(v) for k, v in raw["starting_resources"].items()},
        rank_thresholds={k: int(v) for k, v in raw["rank_thresholds"].items()},
        cases=cases,
    )


def load_game_content(content_file: Path) -> GameContent:
    with content_file.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return _parse_game_content(raw)


def _rank_for_experience(experience: int, thresholds: dict[str, int]) -> str:
    rank = "Trainee"
    for label, minimum in sorted(thresholds.items(), key=lambda item: item[1]):
        if experience >= minimum:
            rank = label
    return rank


def _infer_action_from_text(free_text: str, actions: list[Action]) -> Action | None:
    tokens = {token for token in free_text.lower().split() if token}
    best_score = 0
    best_action: Action | None = None
    for action in actions:
        action_tokens = set(action.text.lower().replace("/", " ").replace("-", " ").split())
        overlap = len(tokens.intersection(action_tokens))
        if overlap > best_score:
            best_score = overlap
            best_action = action
    return best_action if best_score > 0 else None


def _save_progress(save_file: Path, progress: dict) -> None:
    save_file.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def _load_progress(save_file: Path) -> dict | None:
    if not save_file.exists():
        return None
    with save_file.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _apply_action(action: Action, resources: dict[str, int]) -> None:
    for name, cost in action.costs.items():
        resources[name] = resources.get(name, 0) - cost


def _difficulty_bonus(difficulty: str) -> int:
    return {"easy": 5, "intermediate": 10, "advanced": 15}.get(difficulty.lower(), 5)


def _select_option(
    prompt: str,
    valid_keys: set[str],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> str:
    while True:
        selected = input_fn(prompt).strip().upper()
        if selected in valid_keys:
            return selected
        output_fn("Invalid option. Choose one of: " + ", ".join(sorted(valid_keys)))


def _run_case(
    case: Case,
    profile: PlayerProfile,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> dict:
    resources = dict(profile.capacity)
    exhausted_before_submission = False
    discovered_evidence: list[str] = []
    actions_taken: list[str] = []
    risk_indicators: list[str] = []

    evidence_lookup = {item.evidence_id: item for item in case.evidence}
    action_lookup = {action.key: action for action in case.actions}
    conclusion_lookup = {item.key: item for item in case.conclusions}

    output_fn(f"\nCase: {case.title} ({case.difficulty.title()})")
    output_fn(case.opening)
    output_fn("Characters: " + ", ".join(case.characters))
    output_fn("Entities: " + ", ".join(case.entities))

    while True:
        remaining_actions = [item for item in case.actions if item.key not in actions_taken]

        output_fn("\nCase details discovered so far:")
        if discovered_evidence:
            for evidence_id in discovered_evidence:
                output_fn(f"- {evidence_lookup[evidence_id].description}")
        else:
            output_fn("- No evidence discovered yet")

        output_fn(
            f"Resources -> Time: {resources['time']} | Budget: {resources['budget']} | Energy: {resources['energy']}"
        )
        output_fn("Actions:")
        for action in remaining_actions:
            output_fn(
                f"  [{action.key}] {action.text} (cost T{action.costs['time']} B{action.costs['budget']} E{action.costs['energy']})"
            )
        output_fn("  [F] Free text action")
        output_fn("  [S] Submit final conclusion")
        output_fn("  [G] Give up case")

        valid_keys = {item.key for item in remaining_actions}.union({"F", "S", "G"})
        selected = _select_option("Choose an action: ", valid_keys, input_fn, output_fn)

        if selected == "G":
            return {
                "solved": False,
                "gave_up": True,
                "selected_conclusion": None,
                "score": 0,
                "xp_gained": 0,
                "capacity_increase": 0,
                "actions_taken": actions_taken,
                "discovered_evidence": discovered_evidence,
                "risk_indicators": risk_indicators,
                "resources": resources,
            }

        if selected == "S" or not remaining_actions:
            output_fn("Conclusions:")
            for conclusion in case.conclusions:
                output_fn(f"  [{conclusion.key}] {conclusion.label}")
            conclusion_key = _select_option(
                "Select conclusion: ", set(conclusion_lookup), input_fn, output_fn
            )
            is_correct = conclusion_key == case.correct_conclusion
            discovered = [evidence_lookup[item] for item in discovered_evidence]
            red_flags_identified = sum(1 for item in discovered if item.is_red_flag_easy)
            missed_evidence = [item.evidence_id for item in case.evidence if item.evidence_id not in discovered_evidence]
            resource_left = max(resources["time"], 0) + max(resources["budget"], 0) + max(resources["energy"], 0)

            base_score = 60 if is_correct else 20
            score = base_score + len(discovered_evidence) * 3 + red_flags_identified * 5
            if is_correct:
                score += resource_left // 8

            bonus = _difficulty_bonus(case.difficulty)
            xp_gained = bonus if is_correct and not exhausted_before_submission else 0
            if xp_gained:
                profile.experience += xp_gained
                for resource in profile.capacity:
                    profile.capacity[resource] += bonus

            outcome = conclusion_lookup[conclusion_key]
            output_fn(f"\nOutcome: {outcome.label} ({outcome.outcome_type})")
            output_fn(f"Actual activity: {case.actual_activity}")
            output_fn("Key AML/KYC red flags: " + "; ".join(case.key_red_flags))
            if missed_evidence:
                output_fn("Missed evidence IDs: " + ", ".join(missed_evidence))
            output_fn("Recommended approach: " + case.recommended_approach)
            if exhausted_before_submission and is_correct:
                output_fn("You solved the case but exhausted resources first, so no experience was awarded.")
            output_fn(f"Case score: {score} | Experience gained: {xp_gained}")

            return {
                "solved": is_correct,
                "gave_up": False,
                "selected_conclusion": conclusion_key,
                "score": score,
                "xp_gained": xp_gained,
                "capacity_increase": bonus if xp_gained else 0,
                "actions_taken": actions_taken,
                "discovered_evidence": discovered_evidence,
                "risk_indicators": risk_indicators,
                "resources": resources,
            }

        if selected == "F":
            free_text = input_fn("Describe your action: ").strip()
            inferred = _infer_action_from_text(free_text, remaining_actions)
            if inferred is None:
                resources["time"] -= 2
                resources["energy"] -= 2
                output_fn("The lead was too vague. You spent effort but uncovered nothing conclusive.")
            else:
                selected = inferred.key
                output_fn(f"Interpreted free text as action [{selected}] {inferred.text}")

        if selected in action_lookup and selected not in actions_taken:
            action = action_lookup[selected]
            actions_taken.append(selected)
            _apply_action(action, resources)
            for evidence_id in action.reveals_evidence:
                if evidence_id not in discovered_evidence:
                    discovered_evidence.append(evidence_id)
            if action.risk_indicator and action.risk_indicator not in risk_indicators:
                risk_indicators.append(action.risk_indicator)
            output_fn(action.narrative)

        if not exhausted_before_submission and any(value <= 0 for value in resources.values()):
            exhausted_before_submission = True


def play_game(
    content: GameContent,
    save_file: Path,
    progress: dict | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> dict:
    if progress is None:
        profile = PlayerProfile(
            experience=0,
            capacity=dict(content.starting_resources),
        )
        game_progress = {"current_case_index": 0, "case_history": []}
    else:
        saved_profile = progress["profile"]
        profile = PlayerProfile(
            experience=int(saved_profile["experience"]),
            capacity={k: int(v) for k, v in saved_profile["capacity"].items()},
        )
        game_progress = {
            "current_case_index": int(progress.get("current_case_index", 0)),
            "case_history": list(progress.get("case_history", [])),
        }

    output_fn(content.title)
    output_fn("=" * len(content.title))
    output_fn(content.intro)
    output_fn("Disclaimer: " + content.disclaimer)

    for index in range(game_progress["current_case_index"], len(content.cases)):
        case = content.cases[index]
        result = _run_case(case, profile, input_fn, output_fn)

        case_state = {
            "case_id": case.case_id,
            "difficulty": case.difficulty,
            "actions_taken": result["actions_taken"],
            "evidence_discovered": result["discovered_evidence"],
            "evidence_not_discovered": [
                item.evidence_id
                for item in case.evidence
                if item.evidence_id not in result["discovered_evidence"]
            ],
            "characters_interviewed": [
                text for text in result["actions_taken"] if "interview" in text.lower()
            ],
            "player_hypothesis": result["selected_conclusion"],
            "investigation_resources_remaining": result["resources"],
            "suspicion_risk_indicators": result["risk_indicators"],
            "decisions_made": result["actions_taken"],
            "score": result["score"],
            "possible_ending": result["selected_conclusion"],
            "solved": result["solved"],
        }
        game_progress["case_history"].append(case_state)
        game_progress["current_case_index"] = index + 1

        summary = {
            "profile": {
                "experience": profile.experience,
                "capacity": profile.capacity,
                "rank": _rank_for_experience(profile.experience, content.rank_thresholds),
            },
            **game_progress,
        }
        _save_progress(save_file, summary)

        output_fn(
            f"\nCurrent rank: {_rank_for_experience(profile.experience, content.rank_thresholds)} | "
            f"Experience: {profile.experience}"
        )

        if index < len(content.cases) - 1:
            continue_game = _select_option(
                "Request a new case? [Y/N]: ", {"Y", "N"}, input_fn, output_fn
            )
            if continue_game == "N":
                break

    final_summary = {
        "profile": {
            "experience": profile.experience,
            "capacity": profile.capacity,
            "rank": _rank_for_experience(profile.experience, content.rank_thresholds),
        },
        **game_progress,
    }
    _save_progress(save_file, final_summary)
    output_fn("\nSession saved to: " + str(save_file))
    return final_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Play AML Detective, a text-based AML/KYC financial crime investigation game."
    )
    parser.add_argument(
        "--content-file",
        default="game_content.json",
        type=Path,
        help="Path to the JSON document that defines title, cases, and decisions.",
    )
    parser.add_argument(
        "--save-file",
        default="game_progress.json",
        type=Path,
        help="Path to persist game progress between sessions.",
    )
    parser.add_argument(
        "--new-game",
        action="store_true",
        help="Start from case 1 and ignore any existing saved progress.",
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

    progress = None if args.new_game else _load_progress(args.save_file)
    play_game(content=content, save_file=args.save_file, progress=progress)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
