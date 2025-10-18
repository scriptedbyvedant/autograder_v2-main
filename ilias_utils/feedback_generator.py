
import zipfile
import io
from dataclasses import dataclass, field
from typing import List, Tuple

# Assuming the StudentFolder class is defined in zip_parser, we import it.
# This creates a dependency, which is reasonable for this structure.
from .zip_parser import StudentFolder

@dataclass
class FeedbackFile:
    """Represents a file to be included as feedback (e.g., an annotated PDF)."""
    filename: str
    content: bytes

@dataclass
class Feedback:
    """Represents the feedback for a single student."""
    student: StudentFolder
    score: float
    feedback_comment: str
    feedback_files: List[FeedbackFile] = field(default_factory=list)

class FeedbackZipGenerator:
    """Generates a zip file for ILIAS feedback."""

    @staticmethod
    def create_zip(feedback_items: List[Feedback], assignment_name: str) -> io.BytesIO:
        """
        Creates a zip file in memory containing feedback for multiple students.

        Args:
            feedback_items: A list of Feedback objects.
            assignment_name: The name of the assignment, used as the root folder.

        Returns:
            An io.BytesIO object containing the generated zip file data.
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in feedback_items:
                # The path inside the zip for this student's feedback
                # Format: assignment_name/Lastname_Firstname_email_matric/
                student_folder_path = f"{assignment_name}/{item.student.raw_folder}/"

                # 1. Create the feedback text file
                # ILIAS expects a simple text file with the score and comments.
                feedback_content = (
                    f"Gesamtpunktzahl: {item.score}\n\n" # Using German "Gesamtpunktzahl" as is common in ILIAS
                    f"Kommentar:\n{item.feedback_comment}"
                ).encode('utf-8')
                
                feedback_filename = f"{student_folder_path}feedback.txt"
                zf.writestr(feedback_filename, feedback_content)

                # 2. Add any additional feedback files (e.g., annotated PDFs)
                for fb_file in item.feedback_files:
                    file_path = f"{student_folder_path}{fb_file.filename}"
                    zf.writestr(file_path, fb_file.content)

        # Reset buffer position to the beginning before returning
        zip_buffer.seek(0)
        return zip_buffer

    @staticmethod
    def extract_file_from_zip(zip_file: io.BytesIO, file_arcname: str) -> bytes | None:
        """
        Extracts a single file's content from a zip archive.

        Args:
            zip_file: The BytesIO object of the zip archive.
            file_arcname: The full path of the file inside the zip archive.

        Returns:
            The file content as bytes, or None if not found.
        """
        try:
            zip_file.seek(0) # Ensure we read from the beginning
            with zipfile.ZipFile(zip_file, 'r') as z:
                return z.read(file_arcname)
        except (KeyError, zipfile.BadZipFile):
            return None
