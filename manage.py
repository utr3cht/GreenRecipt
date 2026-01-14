#!/usr/bin/env python
import os
import sys

venv_path = os.path.join(os.path.dirname(__file__), '.venv')
if sys.platform == "win32":
    venv_site_packages = os.path.join(venv_path, 'Lib', 'site-packages')
else:
    # Python 3.11を想定
    venv_site_packages = os.path.join(venv_path, 'lib', 'python3.11', 'site-packages')

if venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

def main():
    """管理タスクを実行。"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')
    try:
        from django.core.management import execute_from_command_line  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()