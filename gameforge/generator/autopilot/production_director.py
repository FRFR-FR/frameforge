"""Rule-based production director: budgets, risk register and evidence-led market inputs."""
from __future__ import annotations
from typing import Any

def create_production_plan(spec: dict[str, Any], market_evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    hours=int(spec["campaign"]["target_hours"])
    profile=spec.get("performance",{})
    risks=[
      {"id":"scope","risk":"Campaign scope expands beyond the 5–10 hour target.","mitigation":"Lock chapter count and require a story/gameplay purpose for every optional activity.","gate":"chapter_outline_review"},
      {"id":"performance","risk":"Visual ambition exceeds low-end Android budgets.","mitigation":"Use scalable materials, baked lighting, LODs, occlusion and adaptive resolution; benchmark physical devices.","gate":"device_benchmark"},
      {"id":"narrative","risk":"Generated dialogue creates character or knowledge continuity errors.","mitigation":"Track character knowledge, relationship state and event chronology; run continuity review.","gate":"script_review"},
      {"id":"originality","risk":"A proposed mechanic resembles existing games or patents.","mitigation":"Research prior art and record sources; prototype and conduct legal review where warranted.","gate":"mechanic_review"},
      {"id":"market","risk":"Market assumptions are mistaken for evidence of demand.","mitigation":"Use dated sources, platform search signals and player feedback; label confidence and uncertainty.","gate":"market_evidence_review"}
    ]
    stages=[
      {"id":"concept","deliverable":"Validated GameSpec, audience hypothesis and creative pillars","exit":"Design review passed"},
      {"id":"preproduction","deliverable":"Story bible, complete scene plan, mechanic prototypes and asset bible","exit":"Narrative and mechanic gates passed"},
      {"id":"vertical_slice","deliverable":"One polished 15–30 minute playable section","exit":"External playtest and device benchmark passed"},
      {"id":"production","deliverable":"Complete campaign, 5–10 hours, with authored cinematics","exit":"Feature complete and content locked"},
      {"id":"qa","deliverable":"Regression, accessibility, device and performance test reports","exit":"No critical blockers; target device matrix passed"},
      {"id":"release","deliverable":"Signed Android and Windows builds plus store-ready media","exit":"Reproducible exports and release checklist passed"}
    ]
    evidence=[]
    for item in market_evidence or []:
        if not all(key in item for key in ("source","date","claim")):
            continue
        evidence.append({"source":item["source"],"date":item["date"],"claim":item["claim"],"confidence":item.get("confidence","unrated"),"verified":bool(item.get("verified",False))})
    return {"document_type":"gameforge_production_plan","version":"0.1.0","project_title":spec["title"],
      "generation_mode":"full_autopilot","quality_strategy":"adaptive","campaign_hours":hours,
      "target_platforms":spec["platforms"],"android_profile":profile.get("android_profile","low"),
      "stages":stages,"risk_register":risks,"market_evidence":evidence,
      "market_assessment":"insufficient_evidence" if not evidence else "evidence_attached_requires_human_interpretation",
      "success_policy":"No sales, virality, search ranking or audience-size guarantees. Validate demand with evidence and playtests.",
      "release_ready":False}
