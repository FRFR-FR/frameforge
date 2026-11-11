"""Scene-level narrative planner with deterministic continuity checks."""
from __future__ import annotations

from typing import Any


def build_scene_plan(spec: dict[str, Any], story: dict[str, Any]) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    choices: list[dict[str, Any]] = []
    chapter_count = len(story["chapter_outline"])
    choice_chapters = sorted(set((max(1, round(chapter_count * 0.25)), max(1, round(chapter_count * 0.6)), max(1, round(chapter_count * 0.82)))))
    previous_flag: str | None = None

    for chapter in story["chapter_outline"]:
        number = chapter["chapter"]
        prefix = f"ch{number:02d}"
        inherited = [previous_flag] if previous_flag and number > 1 else []
        beats = [
            ("arrival", "Explore", "Establish the chapter's location, immediate objective and environmental clue.", "The player discovers a detail that reframes the current objective."),
            ("pressure", "Confront", "Put the chapter objective under pressure through an obstacle or relationship conflict.", "The protagonist must act rather than defer the central problem."),
        ]
        for index, (suffix, kind, objective, turn) in enumerate(beats, start=1):
            scenes.append({
                "scene_id": f"{prefix}_{suffix}",
                "chapter": number,
                "sequence": index,
                "scene_type": kind.lower(),
                "player_objective": objective,
                "dramatic_turn": turn,
                "gameplay_beat": chapter["gameplay_focus"],
                "emotional_focus": chapter["emotional_focus"],
                "requires_flags": inherited if index == 1 else [],
                "sets_flags": [],
                "dialogue_intent": "Reveal character priorities through subtext; avoid exposition that the player already knows.",
            })

        if number in choice_chapters:
            flag = f"choice_ch{number:02d}_approach"
            choice = {
                "choice_id": f"{prefix}_major_choice",
                "chapter": number,
                "state_key": flag,
                "prompt": "Choose how the protagonist responds to the chapter's central conflict.",
                "options": [
                    {"id": "protect", "label": "Protect the relationship", "consequence": "Prioritise trust and immediate safety."},
                    {"id": "reveal", "label": "Reveal the difficult truth", "consequence": "Prioritise disclosure and long-term accountability."},
                ],
                "design_rule": "Both options preserve forward progress; later dialogue and relationship state acknowledge the chosen approach.",
            }
            choices.append(choice)
            previous_flag = flag
            sets = [flag]
        else:
            sets = []

        scenes.append({
            "scene_id": f"{prefix}_turn",
            "chapter": number,
            "sequence": 3,
            "scene_type": "decision" if sets else "payoff",
            "player_objective": chapter["dramatic_purpose"],
            "dramatic_turn": "Resolve the chapter question and establish the next playable objective.",
            "gameplay_beat": chapter["gameplay_focus"],
            "emotional_focus": chapter["emotional_focus"],
            "requires_flags": inherited,
            "sets_flags": sets,
            "choice_id": f"{prefix}_major_choice" if sets else None,
            "dialogue_intent": "Let the characters react to what happened; preserve established knowledge and emotional continuity.",
        })

    plan = {
        "document_type": "gameforge_scene_plan",
        "version": "0.1.0",
        "project_title": spec["title"],
        "scene_count": len(scenes),
        "choice_count": len(choices),
        "branching_strategy": "convergent_story_with_persistent_choice_state",
        "scenes": scenes,
        "choices": choices,
        "continuity_validation": validate_scene_plan(scenes, choices, chapter_count),
        "status": "scene_cards_generated_not_scripted_or_playtested",
    }
    return plan


def validate_scene_plan(scenes: list[dict[str, Any]], choices: list[dict[str, Any]], chapter_count: int) -> dict[str, Any]:
    errors: list[str] = []
    scene_ids = [scene["scene_id"] for scene in scenes]
    if len(scene_ids) != len(set(scene_ids)):
        errors.append("Scene IDs must be unique.")

    choice_keys = {choice["state_key"] for choice in choices}
    choice_ids = {choice["choice_id"] for choice in choices}
    for scene in scenes:
        if scene["chapter"] < 1 or scene["chapter"] > chapter_count:
            errors.append(f"{scene['scene_id']} references an invalid chapter.")
        for flag in scene["requires_flags"]:
            if flag not in choice_keys:
                errors.append(f"{scene['scene_id']} requires undeclared state key {flag}.")
        for flag in scene["sets_flags"]:
            if flag not in choice_keys:
                errors.append(f"{scene['scene_id']} sets undeclared state key {flag}.")
        if scene["choice_id"] is not None and scene["choice_id"] not in choice_ids:
            errors.append(f"{scene['scene_id']} references an undeclared choice.")

    for choice in choices:
        if len(choice["options"]) < 2:
            errors.append(f"{choice['choice_id']} must have at least two options.")
        if len({option["id"] for option in choice["options"]}) != len(choice["options"]):
            errors.append(f"{choice['choice_id']} has duplicate option IDs.")

    return {"passed": not errors, "errors": errors, "checks": ["unique_scene_ids", "chapter_bounds", "declared_choice_state", "choice_references", "distinct_choice_options"]}
