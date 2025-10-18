# ilias_utils/feedback_zip.py
import os
import json
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional

"""
Build a feedback ZIP compatible with ILIAS "multi_feedback" uploads.

Layout produced:
  <ROOT>/
    <raw_folder_1>/
      feedback.json
      feedback.txt
    <raw_folder_2>/
      ...

ROOT name is copied from a reference feedback zip if provided; else synthesized.
"""


def _read_root_from_reference(reference_feedback_zip: str) -> Optional[str]:
    if not reference_feedback_zip or not os.path.isfile(reference_feedback_zip):
        return None
    try:
        with zipfile.ZipFile(reference_feedback_zip, "r") as z:
            for info in z.infolist():
                arc = info.filename.replace("\\", "/")
                if arc.endswith("/") and arc.count("/") == 1:
                    return arc  # keep trailing slash
    except Exception:
        return None
    return None


def _synth_root(assignment_name: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    return f"multi_feedback_{assignment_name}_{ts}/"


def _render_feedback_txt(student_result: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"Overall Score: {student_result.get('overall_score', '—')}")
    if student_result.get("instructor_note"):
        lines.append(f"Instructor Note: {student_result['instructor_note']}")
    lines.append("")
    lines.append("Per-question feedback:")
    for it in student_result.get("items", []):
        qid = it.get("question_id", "Q?")
        tscore = it.get("total_score", "—")
        lines.append(f"- {qid}: {tscore}")
        rb = it.get("rubric_scores", [])
        if rb:
            parts = [f"{r['criteria']}: {r['score']}/{r['max_score']}" for r in rb]
            lines.append(f"  Rubric: " + "; ".join(parts))
        if it.get("feedback_text"):
            lines.append(f"  Feedback: {it['feedback_text']}")
        if it.get("explanation"):
            lines.append(f"  Explanation: {it['explanation']}")
    return "\n".join(lines) + "\n"


def build_feedback_zip(
    ingest_manifest: Dict[str, Any],
    graded_results: List[Dict[str, Any]],
    out_zip_path: str,
    reference_feedback_zip: Optional[str] = None,
) -> str:
    """
    Creates a feedback ZIP with:
      <ROOT>/
        <raw_folder>/
          feedback.json
          feedback.txt

    <raw_folder> values are reused EXACTLY from ingest_manifest['student_folders'][*]['raw_folder'].
    """
    results_by_raw = {r["raw_folder"]: r for r in graded_results}

    root = _read_root_from_reference(reference_feedback_zip) or _synth_root(ingest_manifest["assignment_name"])
    if not root.endswith("/"):
        root += "/"

    with zipfile.ZipFile(out_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(root, b"")

        for sf in ingest_manifest.get("student_folders", []):
            sraw = sf["raw_folder"]
            student_dir = f"{root}{sraw}/"
            z.writestr(student_dir, b"")

            result = results_by_raw.get(sraw)
            if not result:
                placeholder = {
                    "message": "No feedback generated for this submission.",
                    "raw_folder": sraw,
                }
                z.writestr(student_dir + "feedback.json", json.dumps(placeholder, ensure_ascii=False, indent=2))
                z.writestr(student_dir + "feedback.txt", "No feedback generated for this submission.\n")
                continue

            z.writestr(student_dir + "feedback.json", json.dumps(result, ensure_ascii=False, indent=2))
            z.writestr(student_dir + "feedback.txt", _render_feedback_txt(result))

    return out_zip_path
