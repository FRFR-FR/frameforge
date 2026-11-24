#!/usr/bin/env python3
"""Strict NOAA-only gate for the Ocean Nightmares full render."""
import json, sys
from pathlib import Path
p=Path("projects/ocean-nightmares/media_manifest.json")
m=json.loads(p.read_text(encoding="utf-8"))
errors=[]
policy=m.get("source_policy",{})
if policy.get("pixabay") is not False or policy.get("other_sources") is not False:
    errors.append("Only NOAA Ocean Exploration is permitted.")
clips=m.get("clips",[])
target=int(m.get("requirements",{}).get("minimum_unique_clips",30))
if len(clips)<target: errors.append(f"Need at least {target} clip entries; found {len(clips)}.")
ids=[c.get("id") for c in clips]
if len(set(ids))!=len(ids): errors.append("Clip IDs must be unique.")
for c in clips:
    if c.get("approved") is not True: errors.append(f'{c.get("id")}: not approved.')
    if c.get("rights_review")!="approved": errors.append(f'{c.get("id")}: rights review incomplete.')
    if c.get("species_review")!="approved": errors.append(f'{c.get("id")}: species review incomplete.')
    if c.get("species") not in m.get("species_order",[]): errors.append(f'{c.get("id")}: species missing/invalid.')
    url=(c.get("noaa_page_url") or "")+" "+(c.get("direct_media_url") or "")
    if "noaa.gov" not in url.lower(): errors.append(f'{c.get("id")}: NOAA source URL missing.')
if len({c.get("direct_media_url") for c in clips if c.get("approved") is True})<target:
    errors.append(f"Need {target} distinct approved media URLs.")
if errors:
    print("RENDER BLOCKED — footage gate not satisfied:")
    for e in errors: print(" - "+e)
    sys.exit(2)
print("NOAA FOOTAGE GATE PASSED")
