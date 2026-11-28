#!/usr/bin/env python3
"""Apply explicit, filename-specific visual decisions after reviewing B-roll contact sheets."""
from pathlib import Path
import argparse
import csv
import json
from datetime import datetime, timezone

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--episode-dir",required=True)
    args=parser.parse_args()
    root=Path(args.episode_dir).resolve()
    manifest_path=root/"asset-manifest-broll.csv"
    decision_path=root/"assets"/"visual-review-decisions.json"
    index_path=root/"output"/"broll_review"/"review_index.json"

    if not manifest_path.is_file():
        raise SystemExit("Visual review blocked: no acquired asset manifest exists.")
    if not decision_path.is_file():
        raise SystemExit("Visual review blocked: explicit visual-review-decisions.json is missing.")

    payload=json.loads(decision_path.read_text(encoding="utf-8"))
    reviewer=str(payload.get("reviewer","")).strip()
    reviewed_at=str(payload.get("reviewed_at","")).strip()
    decisions=payload.get("decisions",[])
    if not reviewer or not reviewed_at or not isinstance(decisions,list):
        raise SystemExit("Visual review decision file must contain reviewer, reviewed_at and decisions[].")

    by_name={}
    for decision in decisions:
        filename=str(decision.get("filename","")).replace("\\","/").strip()
        status=str(decision.get("status","")).upper().strip()
        reason=str(decision.get("reason","")).strip()
        if not filename or status not in ("APPROVED","REJECTED") or len(reason)<20:
            raise SystemExit(f"Invalid visual decision for {filename or '<missing filename>'}: status and a reason of at least 20 characters are required.")
        if filename in by_name:
            raise SystemExit(f"Duplicate visual decision: {filename}")
        by_name[filename]=decision

    with manifest_path.open(newline="",encoding="utf-8") as handle:
        rows=list(csv.DictReader(handle))
        fields=list(rows[0].keys()) if rows else []
    if not rows:
        raise SystemExit("Visual review blocked: manifest contains no acquired clips.")
    for extra in ("visual_review_status","visual_review_reason","visual_reviewer","visual_reviewed_at"):
        if extra not in fields: fields.append(extra)

    known={row["filename"].replace("\\","/") for row in rows}
    unknown=sorted(set(by_name)-known)
    if unknown:
        raise SystemExit("Decision file contains filenames not present in the acquired manifest: "+", ".join(unknown[:5]))

    approved=0
    for row in rows:
        filename=row["filename"].replace("\\","/")
        decision=by_name.get(filename)
        if decision:
            row["visual_review_status"]=decision["status"].upper()
            row["visual_review_reason"]=decision["reason"].strip()
            row["visual_reviewer"]=reviewer
            row["visual_reviewed_at"]=reviewed_at
            if decision["status"].upper()=="APPROVED":
                if row.get("relevance_level")!="subject-specific":
                    raise SystemExit(f"Context-only footage cannot be approved as subject-specific: {filename}")
                approved+=1
        else:
            row["visual_review_status"]="PENDING"
            row["visual_review_reason"]=""
            row["visual_reviewer"]=""
            row["visual_reviewed_at"]=""

    with manifest_path.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    if index_path.is_file():
        index=json.loads(index_path.read_text(encoding="utf-8"))
        for item in index:
            filename=item.get("filename","").replace("\\","/")
            decision=by_name.get(filename)
            item["review_status"]=decision["status"].upper() if decision else "PENDING visual review"
            item["review_reason"]=decision.get("reason","") if decision else ""
            item["reviewer"]=reviewer if decision else ""
            item["reviewed_at"]=reviewed_at if decision else ""
        index_path.write_text(json.dumps(index,indent=2),encoding="utf-8")

    report={
        "status":"VISUAL_DECISIONS_APPLIED",
        "reviewer":reviewer,
        "reviewed_at":reviewed_at,
        "manifest_clips":len(rows),
        "approved_subject_specific_clips":approved,
        "pending_clips":sum(row.get("visual_review_status")=="PENDING" for row in rows),
        "rejected_clips":sum(row.get("visual_review_status")=="REJECTED" for row in rows),
        "approval_rule":"Only explicitly listed APPROVED filenames with a written visual reason enter the edit."
    }
    (root/"output"/"visual_review_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    if approved<40:
        raise SystemExit(f"Only {approved} explicitly approved subject-specific clips; at least 40 are needed for this documentary.")

if __name__=="__main__":
    main()
