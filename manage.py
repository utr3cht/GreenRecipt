#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Add the virtual environment's site-packages to the path
# This assumes the virtual environment is named '.venv' and is in the project root
venv_path = os.path.join(os.path.dirname(__file__), '.venv')
if sys.platform == "win32":
    venv_site_packages = os.path.join(venv_path, 'Lib', 'site-packages')
else:
    # Assuming Python 3.11 based on previous outputs
    venv_site_packages = os.path.join(venv_path, 'lib', 'python3.11', 'site-packages')

if venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

def main():
    """Run administrative tasks."""
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