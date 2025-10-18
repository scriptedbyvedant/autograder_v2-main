# ilias_utils/manifest_adapter.py
from typing import Dict, Any, List
from .models import IngestResult

def build_items_from_ingest(
    ingest: IngestResult | Dict[str, Any],
    question_manifest: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Convert IngestResult into grading items using an assignment-specific question manifest.

    question_manifest example:
    {
      "assignment_id": "A1",
      "questions": [
        {
          "question_id": "Q1",
          "type_hint": "code",
          "rubric_items": [...],
          "resources": {"tests_py": "..."},
          "file_globs": ["*.py"]
        },
        ...
      ]
    }
    """
    from fnmatch import fnmatch

    ingest_dict: Dict[str, Any] = ingest if isinstance(ingest, dict) else ingest.to_dict()
    items: List[Dict[str, Any]] = []
    questions = question_manifest.get("questions", [])

    for sf in ingest_dict.get("student_folders", []):
        for q in questions:
            file_globs = q.get("file_globs", [])
            matching_arcnames: List[str] = []

            for f in sf.get("files", []):
                if not file_globs:
                    continue
                if any(fnmatch(f["filename"], pat) for pat in file_globs):
                    matching_arcnames.append(f["arcname"])

            item: Dict[str, Any] = {
                "student": {
                    "lastname": sf.get("lastname"),
                    "firstname": sf.get("firstname"),
                    "email": sf.get("email"),
                    "matric": sf.get("matric"),
                    "raw_folder": sf.get("raw_folder"),
                },
                "question_id": q["question_id"],
                "type_hint": q.get("type_hint"),
                "rubric_items": q.get("rubric_items", []),
                "rubric_text": q.get("rubric_text", ""),
                "answer_files": [],                         # physical paths if extracted later
                "answer_file_arcnames": matching_arcnames,  # inside-zip references
                "answer_text": None,
                "answer_numeric": None,
                "answer_mcq": None,
                "meta": q.get("meta", {}),
                "resources": q.get("resources", {}),
            }

            items.append(item)

    return items
