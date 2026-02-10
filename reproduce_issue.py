
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')
django.setup()

from core.models import Coupon, EcoProduct
from core.forms import StoreCouponForm, StoreEcoProductForm
from django.core.exceptions import ValidationError

def test_coupon_validation():
    print("\n--- Testing Coupon Validation ---")
    
    # Test Model Validation directly (if validators were there)
    print("Attempting to create Coupon with negative discount_value...")
    coupon = Coupon(
        title="Test Coupon",
        description="Test",
        type="absolute",
        discount_value=-100,
        required_points=-50
    )
    try:
        coupon.full_clean()
        print("[FAIL] Coupon model accepted negative values.")
    except ValidationError as e:
        print(f"[PASS] Coupon model rejected negative values: {e}")
    except Exception as e:
        print(f"[ERROR] Coupon model raised unexpected exception: {e}")

    # Test Form Validation
    print("\nAttempting to validate StoreCouponForm with negative values...")
    form_data = {
        'title': 'Test Coupon Form',
        'type': 'absolute',
        'discount_value': -100,
        'requirement': 'None',
        'required_points': -50,
        'description': 'Test',
        'remarks': 'Test'
    }
    form = StoreCouponForm(data=form_data)
    if form.is_valid():
        print("[FAIL] StoreCouponForm accepted negative values.")
    else:
        print(f"[PASS] StoreCouponForm rejected negative values: {form.errors}")

def test_ecoproduct_validation():
    print("\n--- Testing EcoProduct Validation ---")
    
    # Test Model Validation directly
    print("Attempting to create EcoProduct with negative points...")
    eco_product = EcoProduct(
        name="Test Eco Product",
        points=-10
    )
    try:
        eco_product.full_clean()
        print("[FAIL] EcoProduct model accepted negative values.")
    except ValidationError as e:
        print(f"[PASS] EcoProduct model rejected negative values: {e}")
    except Exception as e:
        print(f"[ERROR] EcoProduct model raised unexpected exception: {e}")

    # Test Form Validation
    print("\nAttempting to validate StoreEcoProductForm with negative values...")
    form_data = {
        'name': 'Test Eco Product Form',
        'points': -10,
        'remarks': 'Test'
    }
    form = StoreEcoProductForm(data=form_data)
    if form.is_valid():
        print("[FAIL] StoreEcoProductForm accepted negative values.")
    else:
        print(f"[PASS] StoreEcoProductForm rejected negative values: {form.errors}")

if __name__ == "__main__":
    test_coupon_validation()
    test_ecoproduct_validation()
