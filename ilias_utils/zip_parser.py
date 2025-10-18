
# File: ilias_utils/zip_parser.py

import os
import re
import json
import zipfile
import mimetypes
import io
import concurrent.futures
from typing import Optional, Tuple, List, Iterable, Dict, Union, Any

from grader_engine.pdf_parser_multimodal import extract_multimodal_content_from_pdf
from .models import StudentFile, StudentFolder, IngestResult

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MATRIC_RE = re.compile(r"^[A-Za-z0-9._\-\/]+$")  # relaxed for some IDs


def _guess_mime(filename: str) -> str:
    mt, _ = mimetypes.guess_type(filename)
    return mt or "application/octet-stream"


def parse_student_folder_name(folder_name: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    name = folder_name.strip("/")
    if "_" in name and " " not in name:
        parts = name.split("_")
        if len(parts) >= 3:
            email_idx = next((i for i, t in enumerate(parts) if "@" in t), None)
            if email_idx is not None:
                email = parts[email_idx]
                matric = parts[-1] if MATRIC_RE.match(parts[-1]) else None
                lastname = parts[0] if parts else None
                firstname_tokens = parts[1:email_idx] if email_idx > 1 else []
                firstname = " ".join(firstname_tokens) if firstname_tokens else None
                if EMAIL_RE.match(email):
                    return lastname, firstname, email, matric
    tokens = name.split()
    if len(tokens) >= 3:
        email_idx = next((i for i, t in enumerate(tokens) if EMAIL_RE.match(t)), None)
        if email_idx is not None:
            email = tokens[email_idx]
            matric = tokens[-1] if MATRIC_RE.match(tokens[-1]) else None
            name_tokens = tokens[:email_idx]
            lastname = name_tokens[0] if name_tokens else None
            firstname = " ".join(name_tokens[1:]) if len(name_tokens) > 1 else None
            return lastname, firstname, email, matric
    return None, None, None, None


def _iter_zip(z: zipfile.ZipFile) -> Iterable[zipfile.ZipInfo]:
    for info in z.infolist():
        if '__MACOSX' in info.filename or '.DS_Store' in info.filename:
            continue
        info.filename = info.filename.replace("\\", "/")
        yield info


def _find_single_root(arcs: List[str]) -> str:
    roots = [a for a in arcs if a.endswith("/") and a.count("/") == 1]
    return roots[0] if len(roots) == 1 else ""


def _find_case_insensitive_submissions_root(arcs: List[str], root: str) -> Optional[str]:
    for a in arcs:
        if not a.startswith(root): continue
        rel = a[len(root):]
        if not rel: continue
        if rel.endswith("/") and rel.count("/") == 1:
            first = rel[:-1]
            if first.lower() == "submissions":
                return root + first + "/"
    for a in arcs:
        if not a.startswith(root): continue
        rel = a[len(root):]
        if not rel: continue
        seg = rel.split("/", 1)[0]
        if seg and seg.lower() == "submissions":
            return root + seg + "/"
    return None


def _ensure_student(student_map: Dict[str, StudentFolder], sdir: str) -> StudentFolder:
    if sdir in student_map:
        return student_map[sdir]
    ln, fn, em, ma = parse_student_folder_name(sdir)
    # Ensure the answers dict is initialized
    sf = StudentFolder(raw_folder=sdir, lastname=ln, firstname=fn, email=em, matric=ma, files=[], answers={})
    student_map[sdir] = sf
    return sf

def _process_pdf_content(zip_file, arc_name: str, extractor) -> List[Any]:
    """Helper function to run in a separate thread."""
    try:
        with zip_file.open(arc_name) as pdf_file:
            pdf_bytes = pdf_file.read()
            return extractor(io.BytesIO(pdf_bytes))
    except Exception as e:
        print(f"Error processing PDF {arc_name} in thread: {e}")
        return []

def parse_ilias_zip(zip_path_or_file: Union[str, io.BytesIO], multimodal_extractor=None) -> IngestResult:
    excel_candidate: Optional[str] = None
    student_map: Dict[str, StudentFolder] = {}
    
    if isinstance(zip_path_or_file, str):
        if not os.path.isfile(zip_path_or_file):
            raise FileNotFoundError(zip_path_or_file)
        if not zip_path_or_file.lower().endswith(".zip"):
            raise ValueError("Expected a .zip ILIAS export")
        assignment_name = os.path.splitext(os.path.basename(zip_path_or_file))[0]
    else:
        assignment_name = "assignment"

    with zipfile.ZipFile(zip_path_or_file, "r") as z:
        arcs = [i.filename.replace("\\", "/") for i in z.infolist()]
        root = _find_single_root(arcs)
        if not isinstance(zip_path_or_file, str) and root:
            assignment_name = root.strip('/')
        
        # ... (excel candidate finding logic remains the same)

        handled_any = False
        prefixes: List[str] = []
        if root:
            subdir = _find_case_insensitive_submissions_root(arcs, root)
            if subdir:
                prefixes.append(subdir)
        prefixes.append("submissions/")
        
        # --- Start of Parallelized Grading ---
        
        pdf_processing_tasks = {}
        
        # First Pass: Discover all files and create StudentFile objects without content
        for pref in prefixes:
            if any(a.startswith(pref) for a in arcs):
                handled_any = True
                for info in _iter_zip(z):
                    arc = info.filename
                    if not arc.startswith(pref) or info.is_dir(): continue
                    rel = arc[len(pref):]
                    if not rel: continue
                    parts = rel.split("/", 1)
                    if len(parts) < 2: continue
                    sdir, file_rel = parts
                    
                    st = _ensure_student(student_map, sdir)
                    fname = os.path.basename(file_rel)
                    
                    # Create StudentFile but leave multimodal_content empty for now
                    student_file = StudentFile(arcname=arc, filename=fname, size=info.file_size, content_type=_guess_mime(fname), multimodal_content=[])
                    st.files.append(student_file)

                    # If it's a PDF and we have an extractor, schedule it for processing
                    if multimodal_extractor and fname.lower().endswith('.pdf'):
                        # The key is the ZipInfo object, value is the StudentFile to update
                        pdf_processing_tasks[info.filename] = student_file

        # Second Pass (if no submissions folder was found)
        if not handled_any:
            base = root
            for info in _iter_zip(z):
                arc = info.filename
                if (base and not arc.startswith(base)) or info.is_dir(): continue
                rel = arc[len(base):] if base else arc
                if not rel: continue
                parts = rel.split("/", 1)
                if len(parts) < 2: continue
                sdir, file_rel = parts
                if not sdir or "/" in sdir: continue
                
                st = _ensure_student(student_map, sdir)
                fname = os.path.basename(file_rel)
                
                student_file = StudentFile(arcname=arc, filename=fname, size=info.file_size, content_type=_guess_mime(fname), multimodal_content=[])
                st.files.append(student_file)

                if multimodal_extractor and fname.lower().endswith('.pdf'):
                    pdf_processing_tasks[info.filename] = student_file

        # Parallel Execution: Process all scheduled PDFs
        if pdf_processing_tasks and multimodal_extractor:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Map each future to the StudentFile it will update
                future_to_student_file = {
                    executor.submit(_process_pdf_content, z, arc_name, multimodal_extractor): student_file
                    for arc_name, student_file in pdf_processing_tasks.items()
                }
                
                for future in concurrent.futures.as_completed(future_to_student_file):
                    student_file_to_update = future_to_student_file[future]
                    try:
                        # Get the extracted content and update the object
                        extracted_content = future.result()
                        student_file_to_update.multimodal_content = extracted_content
                    except Exception as exc:
                        print(f'Error processing {student_file_to_update.arcname}: {exc}')

    return IngestResult(assignment_name=assignment_name, excel_path=excel_candidate, student_folders=list(student_map.values()))


def parse_ilias_assignment_zip_strict(zip_path: str) -> IngestResult:
    # This function can also be parallelized in a similar manner, 
    # but for now, we focus on the main one.
    if not os.path.isfile(zip_path): raise FileNotFoundError(zip_path)
    if not zip_path.lower().endswith(".zip"): raise ValueError("Expected a .zip ILIAS export")
    with zipfile.ZipFile(zip_path, "r") as z:
        arcs = [i.filename.replace("\\", "/") for i in z.infolist()]
        roots = [a for a in arcs if a.endswith("/") and a.count("/") == 1]
        if len(roots) != 1: raise ValueError(f"Expected exactly one root folder, found: {roots}")
        root = roots[0]
        subdir = _find_case_insensitive_submissions_root(arcs, root)
        if not subdir: raise ValueError(f"No 'submissions' folder found under root (case-insensitive): '{root}<Submissions>/'")
        if not any(a.startswith(subdir) and not a.endswith("/") for a in arcs): raise ValueError(f"No files found under expected submissions dir: '{subdir}'")
        excels_under_root = [a for a in arcs if a.startswith(root) and a.count("/") == 1 and a.lower().endswith((".xlsx", ".xls"))]
        excel_candidate = excels_under_root[0] if excels_under_root else None
        student_map: Dict[str, StudentFolder] = {}
        def ensure_student(sdir: str) -> StudentFolder:
            if sdir in student_map: return student_map[sdir]
            ln, fn, em, ma = parse_student_folder_name(sdir)
            student_map[sdir] = StudentFolder(raw_folder=sdir, lastname=ln, firstname=fn, email=em, matric=ma, files=[], answers={})
            return student_map[sdir]
        student_dirs = set()
        for a in arcs:
            if a.startswith(subdir) and a.endswith("/"): 
                rel = a[len(subdir):].rstrip("/")
                if rel and "/" not in rel: student_dirs.add(rel)
        if not student_dirs:
            for a in arcs:
                if a.startswith(subdir) and not a.endswith("/"): 
                    rel = a[len(subdir):]
                    if "/" in rel: student_dirs.add(rel.split("/", 1)[0])
        if not student_dirs: raise ValueError(f"No student folders found under '{subdir}'")
        for info in z.infolist():
            arc = info.filename.replace("\\", "/")
            if not arc.startswith(subdir) or arc.endswith("/"): continue
            rel = arc[len(subdir):]
            if "/" not in rel: continue
            sdir, tail = rel.split("/", 1)
            if sdir not in student_dirs: continue
            st = ensure_student(sdir)
            fname = os.path.basename(tail)
            extracted_content = []
            if fname.lower().endswith('.pdf'):
                try:
                    with z.open(arc) as pdf_file:
                        pdf_bytes = pdf_file.read()
                        extracted_content = extract_multimodal_content_from_pdf(io.BytesIO(pdf_bytes))
                except Exception as e:
                    print(f"Error processing PDF {arc}: {e}")
            st.files.append(StudentFile(arcname=arc, filename=fname, size=info.file_size, content_type=_guess_mime(fname), multimodal_content=extracted_content))
        assignment_name = os.path.splitext(os.path.basename(zip_path))[0]
        return IngestResult(assignment_name=assignment_name, excel_path=excel_candidate, student_folders=list(student_map.values()))


def save_manifest(result: IngestResult, out_json_path: str) -> None:
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)


def load_manifest(json_path: str) -> IngestResult:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return IngestResult.from_dict(data)


def extract_student_files(zip_path: str, dest_dir: str, only_students: Optional[List[str]] = None) -> int:
    os.makedirs(dest_dir, exist_ok=True)
    selected = set(only_students or [])
    count = 0
    with zipfile.ZipFile(zip_path, "r") as z:
        arcs = [i.filename.replace("\\", "/") for i in z.infolist()]
        root = _find_single_root(arcs)
        prefixes = []
        if root:
            subdir = _find_case_insensitive_submissions_root(arcs, root)
            if subdir: prefixes.append(subdir)
            prefixes.append(root)
        prefixes.append("submissions/")
        for info in _iter_zip(z):
            arc = info.filename
            match_pref = next((p for p in prefixes if arc.startswith(p)), None)
            if not match_pref: continue
            rel = arc[len(match_pref):]
            if not rel: continue
            parts = rel.split("/", 1)
            if len(parts) < 2: continue
            sdir, tail = parts
            if selected and sdir not in selected: continue
            target = os.path.join(dest_dir, sdir, tail)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not info.is_dir():
                with z.open(info, "r") as src, open(target, "wb") as dst:
                    dst.write(src.read())
                    count += 1
    return count
