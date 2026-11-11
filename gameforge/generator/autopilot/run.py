#!/usr/bin/env python3
"""Run GAMEFORGE's first autonomous creative pipeline stages."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator
from providers import get_provider
from narrative_planner import build_scene_plan
from production_director import create_production_plan

ROOT=Path(__file__).resolve().parents[2]
SCHEMA_PATH=ROOT/"schemas"/"game-spec.schema.json"

def validate_spec(spec: dict[str,Any]) -> None:
    schema=json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors=sorted(Draft202012Validator(schema).iter_errors(spec),key=lambda e:list(e.absolute_path))
    if errors:
        detail="\n".join(f"- {'/'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}" for e in errors)
        raise ValueError("Generated GameSpec failed validation:\n"+detail)

def make_story_bible(spec: dict[str,Any], brief: str) -> dict[str,Any]:
    themes=spec["creative_direction"]["themes"]; title=spec["title"]
    count=spec["campaign"]["chapters"]; hours=spec["campaign"]["target_hours"]
    characters=[
      {"id":"protagonist","role":"player character","core_want":"Complete the immediate objective and regain control.","core_need":"Accept that meaningful change requires vulnerability and responsibility.","flaw":"Avoids difficult truths until consequences make avoidance impossible.","arc":"Moves from self-protection toward deliberate, accountable action."},
      {"id":"key_relationship","role":"central companion or emotional counterweight","core_want":"Protect a personal truth or relationship.","conflict":"Their priorities challenge the protagonist's assumptions.","arc":"Trust changes in response to demonstrated choices, not exposition alone."}
    ]
    chapters=[]
    for i in range(1,count+1):
        phase=i/count
        if phase<=.25: act,purpose="establish","Introduce the world, player verbs and central emotional question."
        elif phase<=.55: act,purpose="complicate","Escalate the conflict and make the signature mechanic matter."
        elif phase<=.82: act,purpose="transform","Force a costly choice and reveal consequences of earlier actions."
        else: act,purpose="resolve","Pay off character arcs and deliver an earned, choice-aware conclusion."
        chapters.append({"chapter":i,"act_phase":act,"estimated_minutes":round(hours*60/count),"dramatic_purpose":purpose,"emotional_focus":themes[(i-1)%len(themes)] if themes else "discovery","gameplay_focus":"Introduce, combine or deepen a core player verb; avoid filler objectives.","choice_consequence":"Record a meaningful state change that can be referenced later."})
    return {"document_type":"gameforge_story_bible","version":"0.1.0","project_title":title,"source_brief":brief,"campaign_target_hours":hours,
      "narrative_contract":["Every chapter advances plot, character, world understanding or a core mechanic.","Character change must be demonstrated through action and dialogue continuity.","Choices must have legible consequences; avoid fake binary choices.","The final act must resolve the central dramatic question."],
      "characters":characters,"relationship_model":{"tracked_variables":["trust","disclosure","shared_risk"],"rule":"Update only when a recorded player action or authored event justifies the change."},
      "chapter_outline":chapters,"continuity_checks":["No character references an event before its chapter occurrence.","Every persistent choice has a declared state key and a later payoff or explicit non-payoff.","Character goals and knowledge remain consistent across scenes."],
      "status":"outline_generated_not_scripted_or_playtested"}

def make_mechanic_review(spec: dict[str,Any]) -> dict[str,Any]:
    candidates=[]
    for item in spec.get("mechanics",[]):
        candidates.append({**item,"review":{"prior_art_status":"not_researched","prototype_status":item.get("prototype_status","idea"),
          "test_plan":["Build a greybox interaction with placeholder geometry.","Measure input clarity, failure recovery and repeat-use value.","Test whether the mechanic supports the narrative purpose.","Profile CPU, GPU and memory cost on target hardware."],
          "release_gate":"Do not approve until a playable prototype passes usability and performance tests."}})
    return {"document_type":"gameforge_mechanic_review","version":"0.1.0","candidates":candidates,
      "novelty_policy":"No mechanic is described as unprecedented without documented prior-art research. Similarity review is not proof of originality.",
      "status":"ideas_only_no_playable_prototypes"}

def run_pipeline(brief: str, output: Path, provider_name: str) -> Path:
    if not brief.strip(): raise ValueError("The game brief cannot be empty.")
    provider=get_provider(provider_name); spec=provider.generate_spec(brief); validate_spec(spec)
    output.mkdir(parents=True,exist_ok=True)
    story=make_story_bible(spec,brief)
    scene_plan=build_scene_plan(spec,story)
    if not scene_plan["continuity_validation"]["passed"]:
        raise ValueError("Narrative continuity validation failed: "+str(scene_plan["continuity_validation"]["errors"]))
    mechanics=make_mechanic_review(spec)
    production_plan=create_production_plan(spec)
    report={"pipeline":"gameforge-autopilot","version":"0.2.0","provider":provider.name,"quality_strategy":"adaptive","generation_mode":"full_autopilot",
      "completed":["natural_language_brief_received","gamespec_generated","gamespec_schema_validated","story_bible_outline_generated","scene_cards_generated","narrative_state_continuity_validated","mechanic_review_plan_generated","production_plan_and_risk_register_generated"],
      "not_completed":["full_dialogue_and_scene_script_generation","market_research","original_asset_generation","playable_mechanic_prototypes","vertical_slice_playtest","device_benchmarking","android_apk_export","windows_exe_export"],"release_ready":False}
    artifacts={"GAME_SPEC.json":spec,"STORY_BIBLE.json":story,"SCENE_PLAN.json":scene_plan,"MECHANIC_REVIEW.json":mechanics,"PRODUCTION_PLAN.json":production_plan,"PIPELINE_REPORT.json":report}
    for name,value in artifacts.items():
        (output/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (output/"NEXT_STEPS.md").write_text(f"# {spec['title']} — GAMEFORGE workspace\n\nThe brief was converted into a validated GameSpec, first-pass story outline, scene cards and continuity-checked choice-state plan. This is not a playable or release-ready game.\n\n## Next production gates\n1. Expand scene cards into authored scenes and dialogue.\n2. Research prior art and record sources.\n3. Build greybox prototypes and run usability/performance tests.\n4. Generate/import assets and assemble a playable vertical slice.\n5. Benchmark target devices before APK/EXE packaging.\n",encoding="utf-8")
    return output

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief",required=True,help="Plain-language game idea")
    parser.add_argument("--out",required=True,type=Path,help="Output workspace")
    parser.add_argument("--provider",choices=("offline","openai-compatible"),default="offline")
    args=parser.parse_args()
    try: result=run_pipeline(args.brief,args.out,args.provider)
    except Exception as exc: parser.error(str(exc))
    print(f"GAMEFORGE design pipeline completed: {result}")
    return 0

if __name__=="__main__": raise SystemExit(main())
