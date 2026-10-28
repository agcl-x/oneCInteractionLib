import inspect
import os
from datetime import datetime
import sys
import threading

_log_lock = threading.Lock()

# Determine the root directory of the project importing this library
def _is_system_dir(path: str) -> bool:
    try:
        norm = os.path.abspath(path).lower()
        for prefix in (sys.prefix, sys.base_prefix, getattr(sys, 'exec_prefix', None)):
            if prefix and norm.startswith(os.path.abspath(prefix).lower()):
                return True
    except Exception:
        pass
    return False

env_logs_dir = os.environ.get('ONEC_LOGS_DIR') or os.environ.get('LOGS_DIR')
if env_logs_dir:
    LOGS_DIR = os.path.abspath(env_logs_dir)
else:
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, '__file__') and main_module.__file__:
        candidate = os.path.dirname(os.path.abspath(main_module.__file__))
    elif sys.argv and sys.argv[0]:
        candidate = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        candidate = os.getcwd()

    while candidate and not os.path.isdir(candidate):
        parent = os.path.dirname(candidate)
        if parent == candidate:
            candidate = os.getcwd()
            break
        candidate = parent

    if not candidate or _is_system_dir(candidate):
        project_root = os.getcwd()
    else:
        project_root = candidate

    LOGS_DIR = os.path.join(project_root, 'logs')

def log_sys(message, errorFlag = 0, user_id = None):
    caller_filename = "system"
    try:
        caller_frame = inspect.stack()[1]
        caller_filename = os.path.basename(caller_frame.filename)
    except Exception:
        pass

    log_filename = f"{caller_filename.split('.')[0]}.log"
    log_text = f"[{datetime.now().strftime('%H:%M %d.%m.%Y')}]{'[ERROR]' if errorFlag else '\t'} {message}\n"

    try:
        folder_path = os.path.join(LOGS_DIR, 'system')
        os.makedirs(folder_path, exist_ok=True)
        log_path = os.path.join(folder_path, log_filename)
        log(log_path, log_text)
    except Exception:
        try:
            cwd_folder = os.path.join(os.getcwd(), 'logs', 'system')
            os.makedirs(cwd_folder, exist_ok=True)
            log_path = os.path.join(cwd_folder, log_filename)
            log(log_path, log_text)
        except Exception:
            try:
                prefix = "[ERROR]" if errorFlag else "[INFO]"
                sys.stderr.write(f"{prefix} [{log_filename}] {message}\n")
            except Exception:
                pass

def log(file_path, log_text):
    with _log_lock:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(log_text)
