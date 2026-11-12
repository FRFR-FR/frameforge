"""Pluggable creative providers; offline mode requires no API or network."""
from __future__ import annotations
import json, os, re
from typing import Any, Protocol
from urllib.request import Request, urlopen

class CreativeProvider(Protocol):
    name: str
    def generate_spec(self, brief: str) -> dict[str, Any]: ...

def _title_from_brief(brief: str) -> str:
    for pattern in (r"""(?:called|titled|named)\s+["']([^"']{2,70})["']""", r"""["']([^"']{2,70})["']"""):
        match = re.search(pattern, brief, re.I)
        if match: return match.group(1).strip()
    return " ".join(re.findall(r"[A-Za-z0-9'-]+", brief)[:5]).title() or "Untitled GAMEFORGE Project"

class OfflineCreativeProvider:
    name = "offline"
    def generate_spec(self, brief: str) -> dict[str, Any]:
        text = brief.lower()
        if any(w in text for w in ("horror","scary","survival")):
            genre, visual = "third-person survival horror adventure", "Atmospheric stylised 3D, readable silhouettes, controlled contrast and economical materials."
        elif any(w in text for w in ("racing","race","cars","driving")):
            genre, visual = "arcade driving adventure", "Stylised 3D environments with strong road readability, clear vehicle silhouettes and scalable effects."
        elif any(w in text for w in ("platformer","jump","parkour")):
            genre, visual = "3D action platform adventure", "Expressive painterly 3D forms, layered depth and clear traversal landmarks."
        elif any(w in text for w in ("shooter","combat","battle")):
            genre, visual = "third-person action adventure", "Distinctive stylised 3D spaces, readable silhouettes and measured VFX density."
        else:
            genre, visual = "third-person narrative adventure", "Painterly stylised 3D with deliberate composition, expressive lighting and scalable materials."
        theme_map = {"family":"family","friend":"friendship","memory":"memory","loss":"loss","grief":"grief","identity":"identity","survival":"survival","hope":"hope","betray":"trust","mystery":"discovery","nature":"humanity and nature","choice":"responsibility"}
        themes = list(dict.fromkeys(v for k,v in theme_map.items() if k in text)) or ["identity","responsibility","discovery"]
        match = re.search(r"\b([5-9]|10)\s*(?:hour|hr)", text)
        hours = int(match.group(1)) if match else 7
        return {
          "title":_title_from_brief(brief),"genre":genre,"logline":brief.strip()[:500],
          "player_fantasy":"Master a signature ability, explore a reactive world and make choices that shape the journey.",
          "platforms":["android","windows"],
          "campaign":{"target_hours":hours,"chapters":max(6,min(12,round(hours*1.15))),"side_content_policy":"story_relevant_only"},
          "creative_direction":{"visual_identity":visual,"themes":themes,"narrative_pillars":["the protagonist changes through consequential actions","exploration reveals story through the environment","major choices have understandable emotional consequences"],"reference_exclusions":["unlicensed imitation of named games or franchises","repetitive filler quests and loot-grind padding"]},
          "mechanics":[{"name":"Signature Ability Prototype","player_verb":"interact","story_purpose":"Connect the central player ability to the game's theme and traversal or encounter design.","prior_art_notes":"Prior-art research not yet performed; do not claim novelty.","novelty_confidence":0.1,"prototype_status":"idea"}],
          "performance":{"android_profile":"low","pc_profile":"balanced","baseline_fps":30,"max_download_mb":2500},
          "frameforge":{"enabled":True,"manifest_version":"1.0","cinematic_style":"emotion-led cinematic coverage with clear dialogue and action continuity"}
        }

class OpenAICompatibleProvider:
    """Optional OpenAI-compatible chat-completions adapter; secrets come from env."""
    name = "openai-compatible"
    def __init__(self):
        self.base=os.environ.get("GAMEFORGE_API_BASE","").rstrip("/")
        self.model=os.environ.get("GAMEFORGE_MODEL","")
        self.key=os.environ.get("GAMEFORGE_API_KEY","")
        if not self.base or not self.model: raise ValueError("Set GAMEFORGE_API_BASE and GAMEFORGE_MODEL.")
    def generate_spec(self, brief: str) -> dict[str, Any]:
        from pathlib import Path
        schema=json.loads((Path(__file__).resolve().parents[2]/"schemas"/"game-spec.schema.json").read_text(encoding="utf-8"))
        prompt=("Convert the brief into exactly one JSON object matching this schema. Use Android and Windows, "
          "a 5-10 hour campaign, story-relevant optional content and adaptive low-end performance. "
          "Do not claim market success or mechanic novelty. Set prototype_status to idea unless actually tested.\n"
          f"Schema:\n{json.dumps(schema)}\nBrief:\n{brief}")
        payload={"model":self.model,"temperature":0.7,"response_format":{"type":"json_object"},"messages":[{"role":"user","content":prompt}]}
        headers={"Content-Type":"application/json"}
        if self.key: headers["Authorization"]=f"Bearer {self.key}"
        req=Request(self.base+"/chat/completions",data=json.dumps(payload).encode(),headers=headers,method="POST")
        with urlopen(req,timeout=120) as response: result=json.loads(response.read().decode())
        return json.loads(result["choices"][0]["message"]["content"])

def get_provider(name: str) -> CreativeProvider:
    if name=="offline": return OfflineCreativeProvider()
    if name=="openai-compatible": return OpenAICompatibleProvider()
    raise ValueError(f"Unknown provider: {name}")
