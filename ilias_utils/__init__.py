
# ilias_utils/__init__.py

from .zip_parser import (
    parse_ilias_zip,
    IngestResult,
    StudentFolder,
    StudentFile
)

from .feedback_generator import (
    FeedbackZipGenerator,
    Feedback,
    FeedbackFile
)

__all__ = [
    # from zip_parser
    "parse_ilias_zip",
    "IngestResult",
    "StudentFolder",
    "StudentFile",
    
    # from feedback_generator
    "FeedbackZipGenerator",
    "Feedback",
    "FeedbackFile"
]
