"""
GreenReciptプロジェクトのWSGI設定。
"""

import os

from django.core.wsgi import get_wsgi_application

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')

application = get_wsgi_application()
