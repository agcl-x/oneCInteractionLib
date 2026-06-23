import inspect
import os
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys

# Load config from the shared data folder
COMMON_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.abspath(os.path.join(COMMON_DIR, '..', 'data', 'config.json'))

try:
    with open(CONFIG_PATH, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
except Exception as e:
    config = {}

# LOGS_DIR is resolved dynamically inside the shared work/log/ directory
WORK_DIR = os.path.abspath(os.path.join(COMMON_DIR, '..'))

main_module = sys.modules.get('__main__')
if main_module and hasattr(main_module, '__file__') and main_module.__file__:
    main_dir = os.path.dirname(os.path.abspath(main_module.__file__))
    project_name = os.path.basename(main_dir)
else:
    project_name = 'unknown'

LOGS_DIR = os.path.join(WORK_DIR, 'log', project_name)

def log_usr(message, errorflag = 0, user_id = None):
    folder_path = os.path.join(LOGS_DIR, 'user')
    if user_id is None:
        user_id = "no_ID_user"
    log_path = os.path.join(folder_path, f"{user_id}.log")

    os.makedirs(folder_path, exist_ok=True)

    log_text = f"[{datetime.now().strftime('%H:%M %d.%m.%Y')}]{'[ERROR]' if errorflag else '\t'} {message}\n"
    log(log_path, log_text)

def log_sys(message, errorFlag = 0, user_id = None):
    folder_path = os.path.join(LOGS_DIR, 'system')

    caller_frame = inspect.stack()[1]
    caller_filename = os.path.basename(caller_frame.filename)

    log_path = os.path.join(folder_path, f"{caller_filename.split('.')[0]}.log")

    os.makedirs(folder_path, exist_ok=True)

    log_text = f"[{datetime.now().strftime('%H:%M %d.%m.%Y')}]{'[ERROR]' if errorFlag else '\t'} {message}\n"
    log(log_path, log_text)

def log(file_path, log_text):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(log_text)

def archiveLog():
    format = "zip"
    source_dir = LOGS_DIR

    if not os.path.exists(source_dir):
        log_sys(f"Source directory '{source_dir}' not found. Archiving aborted.", 1)
        return 0

    filename = datetime.now().strftime('%d-%m-%Y')
    config_path = config.get("LogDumpsPath")

    if config_path and os.access(config_path, os.W_OK):
        log_sys("Dump folder path from config is valid")
        base_dump_path = Path(config_path)
    else:
        log_sys("Dump folder path from config is not valid. Dump path set to default")
        base_dump_path = (Path(LOGS_DIR).parent.parent / "logDumps").resolve()

    base_dump_path.mkdir(parents=True, exist_ok=True)

    full_archive_path = base_dump_path / filename

    log_sys(f"Backup path generated: {full_archive_path}.{format}")

    try:
        shutil.make_archive(str(full_archive_path), format, source_dir)
        log_sys(f"Log archive created successfully: {filename}.{format}")
        return 1
    except Exception as e:
        log_sys(f"Error during archiving logs: {e}", 1)
        return 0

def clearLog():
    log_path = LOGS_DIR
    try:
        shutil.rmtree(log_path)
        log_sys(f"Logs cleared")
        return 1
    except Exception as e:
        log_sys(f"Error during clearing logs: {e}", 1)
        return 0
