import zipfile
import os

def validate_zip_structure(zip_path):
    print(f'Analyzing file: {zip_path}')
    if not os.path.exists(zip_path):
        print(f'Error: Zip file not found at {zip_path}')
        return

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            all_files = z.namelist()
            print('\n--- Zip File Contents ---')
            for file in all_files:
                print(file)

            # --- Structure Analysis ---
            print('\n--- Structure Analysis ---')

            # Identify and filter out ignored files from further processing
            ignored_files = [f for f in all_files if '__MACOSX' in f or '.DS_Store' in f]
            valid_files = [f for f in all_files if f not in ignored_files]

            if ignored_files:
                print(f'Found and ignored {len(ignored_files)} macOS-specific files (e.g., __MACOSX, .DS_Store).')

            # Identify the root folder from the valid files
            root_folders = [f for f in valid_files if '/' in f and f.endswith('/') and f.count('/') == 1]
            if len(root_folders) == 1:
                root_folder = root_folders[0]
                print(f'Root folder identified: {root_folder}')
            else:
                root_folder = ''
                print('No single root folder found. Analyzing from the top level.')

            # Check for submission folder within the root
            submission_folder = None
            for folder_name in ['submissions/', 'Submissions/']:
                potential_submission_folder = root_folder + folder_name
                if any(f.startswith(potential_submission_folder) for f in valid_files):
                    submission_folder = potential_submission_folder
                    break
            
            if submission_folder:
                print(f'Submission folder identified: {submission_folder}')
            else:
                print('Warning: No standard "Submissions/" folder found.')

            # --- Student Submissions ---
            student_folders = {}
            base_path = submission_folder if submission_folder else root_folder

            if not base_path:
                print("Could not determine a base path for student submissions.")
            else:
                for file in valid_files:
                    if not file.startswith(base_path) or file.endswith('/'):
                        continue

                    relative_path = file.replace(base_path, '', 1)
                    parts = relative_path.split('/')
                    
                    if len(parts) > 1:
                        student_folder_name = parts[0]
                        if not student_folder_name:
                            continue
                        if student_folder_name not in student_folders:
                            student_folders[student_folder_name] = []
                        student_folders[student_folder_name].append(file)

            if student_folders:
                print('\n--- Student Submissions Found ---')
                for student, files in student_folders.items():
                    print(f'\nStudent: {student}')
                    for file in files:
                        print(f'  - {file}')
            else:
                print('\nWarning: No student submissions could be parsed.')

    except zipfile.BadZipFile:
        print(f'Error: The file at {zip_path} is not a valid zip file.')

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        validate_zip_structure(sys.argv[1])
    else:
        print('Usage: python validate_zip.py <path_to_zip_file>')
