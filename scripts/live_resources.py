"""Read-only deep probe: counts/schema only; sample downloads stay in app data."""

import json
from urllib.parse import urlparse

from diagnostics import error_code, run

from bupt_agent.app import App

FAILED = False


def emit(label, **fields):
    global FAILED
    FAILED |= any(
        value is False for key, value in fields.items() if key == "ok" or key.endswith("_ok")
    )
    print(json.dumps({"check": label, **fields}, ensure_ascii=False), flush=True)


def attachments(value):
    if isinstance(value, dict):
        if isinstance(value.get("resource"), dict):
            yield value["resource"]
        for key, child in value.items():
            if key != "resource":
                yield from attachments(child)
    elif isinstance(value, list):
        for child in value:
            yield from attachments(child)


async def main():
    app = App()
    try:
        grades = await app.invoke("academic.grades", {"term": ""})
        emit(
            "all_term_grades",
            ok=grades["ok"],
            error_code=error_code(grades.get("error")) if not grades["ok"] else None,
            count=len(grades.get("data", {}).get("items", [])),
        )
        courses = (await app.ucloud.courses(page_size=100))["data"]["items"]
        todos = (await app.ucloud.todos())["data"]["items"]
        active = [str(t["course_id"]) for t in todos if t.get("course_id")]
        emit("todo_course_links", total=len(todos), with_course=len(active))
        for todo in [t for t in todos if t["type"] == 3][:2]:
            result = await app.invoke("ucloud.assignment", {"assignment_id": todo["id"]})
            emit(
                "assignment_detail",
                ok=result["ok"],
                error_code=error_code(result.get("error")) if not result["ok"] else None,
                nonempty_content=bool(result.get("data", {}).get("content_html")),
                attachments=len(result.get("data", {}).get("resources") or []),
            )
        order = list(dict.fromkeys(active + [str(c["id"]) for c in courses]))
        sampled_file = False
        for index, course_id in enumerate(order):
            works = await app.invoke("ucloud.assignments", {"course_id": course_id, "page_size": 5})
            result = await app.invoke("ucloud.resources", {"course_id": course_id})
            resources = list(attachments(result.get("data", [])))
            emit(
                "course_content",
                index=index,
                assignments_ok=works["ok"],
                assignment_count=works.get("data", {}).get("total"),
                resources_ok=result["ok"],
                error_code=error_code(result.get("error")) if not result["ok"] else None,
                resource_count=len(resources),
            )
            if not sampled_file:
                for resource in resources:
                    resource_id = str(resource.get("id") or "")
                    extension = (
                        str(resource.get("ext") or resource.get("name", "").rsplit(".", 1)[-1])
                        .lower()
                        .lstrip(".")
                    )
                    if not resource_id or extension not in {"pdf", "docx", "pptx", "txt"}:
                        continue
                    link = await app.invoke("ucloud.resource_url", {"resource_id": resource_id})
                    emit(
                        "resource_preview",
                        ok=link["ok"],
                        error_code=error_code(link.get("error")) if not link["ok"] else None,
                        host=urlparse(link.get("data", {}).get("url", "")).hostname,
                        extension=extension,
                    )
                    if link["ok"]:
                        downloaded = await app.invoke(
                            "ucloud.download", {"resource_id": resource_id, "extension": extension}
                        )
                        emit(
                            "resource_download",
                            ok=downloaded["ok"],
                            error_code=error_code(downloaded.get("error"))
                            if not downloaded["ok"]
                            else None,
                            size=downloaded.get("data", {}).get("bytes"),
                        )
                        if downloaded["ok"]:
                            read = await app.invoke(
                                "files.read",
                                {"path": downloaded["data"]["path"], "max_chars": 2000},
                            )
                            emit(
                                "resource_read",
                                ok=read["ok"],
                                error_code=error_code(read.get("error"))
                                if not read["ok"]
                                else None,
                                units=len(read.get("data", {}).get("units", [])),
                                extracted_chars=sum(
                                    len(u["text"]) for u in read.get("data", {}).get("units", [])
                                ),
                            )
                    sampled_file = True
                    break
            if sampled_file and works["ok"] and works["data"]["items"]:
                break
        emit("download_sample", sampled=sampled_file)
    finally:
        await app.close()
    return 1 if FAILED else 0


if __name__ == "__main__":
    run(main)
