
# ilias_utils/models.py
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class StudentFile:
    arcname: str                 # path inside zip: submissions/<folder>/<file>
    filename: str                # basename.ext
    size: int                    # bytes
    content_type: Optional[str] = None  # guessed content type
    multimodal_content: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StudentFolder:
    raw_folder: str              # "Lastname Firstname email@domain 123456" (or underscore variant)
    lastname: Optional[str]
    firstname: Optional[str]
    email: Optional[str]
    matric: Optional[str]
    files: List[StudentFile] = field(default_factory=list)
    answers: Dict[str, str] = field(default_factory=dict) # NEW: To store parsed answers

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IngestResult:
    assignment_name: str
    student_folders: List[StudentFolder]
    excel_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IngestResult':
        # De-serialize nested StudentFolder objects correctly
        student_folders = []
        for sf_data in data.get("student_folders", []):
            # Extract files and answers if they exist
            files_data = sf_data.pop("files", [])
            answers_data = sf_data.pop("answers", {})
            
            # Create StudentFile objects
            student_files = [StudentFile(**f_data) for f_data in files_data]
            
            # Create StudentFolder object
            sf = StudentFolder(**sf_data, files=student_files, answers=answers_data)
            student_folders.append(sf)

        data["student_folders"] = student_folders
        return cls(**data)
