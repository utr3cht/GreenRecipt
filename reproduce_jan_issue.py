
import os
import django
import sys
from django.core.exceptions import ValidationError

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')
django.setup()

from core.models import EcoProduct
from core.forms import StoreEcoProductForm

def test_jan_validation():
    print("\n--- Testing JAN Code Validation ---")
    
    # Test Model Validation directly
    print("Attempting to create EcoProduct with non-numeric JAN code...")
    eco_product = EcoProduct(
        name="Test Eco Product JAN",
        points=10,
        jan_code="12345ABC" # Invalid JAN code (contains letters)
    )
    try:
        eco_product.full_clean()
        print("[FAIL] EcoProduct model accepted non-numeric JAN code.")
    except ValidationError as e:
        print(f"[PASS] EcoProduct model rejected non-numeric JAN code: {e}")
    except Exception as e:
        print(f"[ERROR] EcoProduct model raised unexpected exception: {e}")

    # Test Form Validation
    print("\nAttempting to validate StoreEcoProductForm with non-numeric JAN code...")
    form_data = {
        'name': 'Test Eco Product Form JAN',
        'points': 10,
        'jan_code': '12345ABC',
        'remarks': 'Test'
    }
    form = StoreEcoProductForm(data=form_data)
    if form.is_valid():
        print("[FAIL] StoreEcoProductForm accepted non-numeric JAN code.")
    else:
        if 'jan_code' in form.errors:
             print(f"[PASS] StoreEcoProductForm rejected non-numeric JAN code: {form.errors['jan_code']}")
        else:
             print(f"[FAIL] StoreEcoProductForm rejected but not for jan_code: {form.errors}")

if __name__ == "__main__":
    test_jan_validation()
