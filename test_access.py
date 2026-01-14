import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')
django.setup()

from django.test import RequestFactory
from django.http import Http404
from core.views import receipt_detail
from accounts.models import CustomUser
from core.models import Receipt
from django.shortcuts import get_object_or_404

def test_receipt_access():
    # Create two users
    user1, _ = CustomUser.objects.get_or_create(username='user1', email='user1@example.com')
    user2, _ = CustomUser.objects.get_or_create(username='user2', email='user2@example.com')
    
    # Create a receipt for user1
    receipt = Receipt.objects.create(user=user1)
    
    # Factory
    factory = RequestFactory()
    
    # Case 1: user1 accesses their own receipt -> Should succeed (return 200)
    request1 = factory.get(f'/result/{receipt.id}/')
    request1.user = user1
    try:
        response = receipt_detail(request1, receipt.id)
        print(f"User1 accessing User1's receipt: Status Code {response.status_code}")
    except Exception as e:
        print(f"User1 accessing User1's receipt failed: {e}")

    # Case 2: user2 accesses user1's receipt -> Should raise Http404
    request2 = factory.get(f'/result/{receipt.id}/')
    request2.user = user2
    try:
        receipt_detail(request2, receipt.id)
        print("User2 accessing User1's receipt: Succeeded (UNEXPECTED)")
    except Http404:
        print("User2 accessing User1's receipt: Raised Http404 (EXPECTED)")
    except Exception as e:
        print(f"User2 accessing User1's receipt raised unexpected exception: {e}")

if __name__ == '__main__':
    test_receipt_access()
