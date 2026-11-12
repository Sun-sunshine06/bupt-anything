"""Bounded read-only feedback/public-source checks; never print personal content or IDs."""

import json
from pathlib import Path

from diagnostics import run, summary

from bupt_agent.app import App
from bupt_agent.common import now


async def main():
    app = App()
    report = {"checked_at": now().isoformat(), "checks": []}

    async def check(name, args=None):
        result = await app.invoke(name, args)
        item = summary(name, result)
        if result["ok"]:
            item["complete"] = result["meta"]["complete"]
            data = result["data"]
            if isinstance(data, dict) and isinstance(data.get("items"), list):
                item["sample_count"] = len(data["items"])
            for key in ("submission_state", "availability"):
                if key in data:
                    item[key] = data[key]
        report["checks"].append(item)
        print(json.dumps(item), flush=True)
        return result

    try:
        for kind in ("shuttle", "events"):
            await check("campus.public_info", {"kind": kind})
        courses = await check("ucloud.courses", {"page_size": 100})
        submission_found = review_found = False
        inspected = 0
        for course in courses.get("data", {}).get("items", [])[:30]:
            listing = await check("ucloud.assignments", {"course_id": str(course["id"])})
            for assignment in listing.get("data", {}).get("items", []):
                if inspected >= 30:
                    break
                inspected += 1
                args = {"assignment_id": str(assignment["id"])}
                submission = await check("ucloud.assignment_submission", args)
                submission_found |= (
                    submission.get("data", {}).get("submission_state") == "record_available"
                )
                # Exercise disabled and enabled lists alike; don't hide a broken
                # empty-response path by skipping assignments without peer review.
                reviews = await check("ucloud.peer_reviews", args)
                if not review_found:
                    accessible = next(
                        (
                            r
                            for r in reviews.get("data", {}).get("items", [])
                            if r["can_enter"] is True
                        ),
                        None,
                    )
                    if accessible:
                        review = await check(
                            "ucloud.peer_review",
                            {**args, "review_id": str(accessible["review_id"])},
                        )
                        review_found = review["ok"]
            if inspected >= 30:
                break
        report["samples"] = {
            "own_submission_read": submission_found,
            "accessible_peer_review_read": review_found,
            "assignments_inspected": inspected,
            "scope": "bounded_samples_not_all_assignments",
        }
    finally:
        await app.close()
        path = Path(__file__).resolve().parents[1] / "artifacts" / "live-feedback-report.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["samples"]), flush=True)
    return 1 if any(not check["ok"] for check in report["checks"]) else 0


if __name__ == "__main__":
    run(main)
