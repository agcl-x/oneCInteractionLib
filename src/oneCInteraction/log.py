import inspect
import os
from datetime import datetime
import sys

# Determine the root directory of the project importing this library
main_module = sys.modules.get('__main__')
if main_module and hasattr(main_module, '__file__') and main_module.__file__:
    project_root = os.path.dirname(os.path.abspath(main_module.__file__))
elif sys.argv and sys.argv[0]:
    project_root = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    project_root = os.getcwd()

# LOGS_DIR is resolved relative to the importing project
LOGS_DIR = os.path.join(project_root, 'logs')

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
