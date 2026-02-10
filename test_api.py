
import os
import django
import sys
import json
from django.test import RequestFactory
from django.urls import reverse

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')
django.setup()

from accounts.views import check_availability
from accounts.models import CustomUser

def test_api():
    print("\n--- Testing Check Availability API ---")
    
    # Ensure test user exists
    email = "test_dup@example.com"
    username = "test_dup_user"
    if not CustomUser.objects.filter(email=email).exists():
        CustomUser.objects.create_user(username=username, email=email, password="password123")
        print(f"Created test user: {username}")
    
    factory = RequestFactory()
    
    # Test 1: Check existing username
    print("\nTest 1: Check existing username")
    request = factory.get('/accounts/check-availability/', {'field': 'username', 'value': username})
    response = check_availability(request)
    data = json.loads(response.content)
    print(f"Response: {data}")
    if data['is_taken']:
        print("[PASS] Correctly identified existing username.")
    else:
        print("[FAIL] Failed to identify existing username.")

    # Test 2: Check new username
    print("\nTest 2: Check new username")
    request = factory.get('/accounts/check-availability/', {'field': 'username', 'value': 'new_unique_user_12345'})
    response = check_availability(request)
    data = json.loads(response.content)
    print(f"Response: {data}")
    if not data['is_taken']:
        print("[PASS] Correctly identified new username.")
    else:
        print("[FAIL] False positive for new username.")

    # Test 3: Check existing email
    print("\nTest 3: Check existing email")
    request = factory.get('/accounts/check-availability/', {'field': 'email', 'value': email})
    response = check_availability(request)
    data = json.loads(response.content)
    print(f"Response: {data}")
    if data['is_taken']:
        print("[PASS] Correctly identified existing email.")
    else:
        print("[FAIL] Failed to identify existing email.")

if __name__ == "__main__":
    test_api()
