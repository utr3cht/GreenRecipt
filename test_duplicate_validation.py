
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')
django.setup()

from accounts.forms import CustomUserCreationForm, StoreUserCreationForm
from accounts.models import CustomUser

def test_duplicate_validation():
    print("\n--- Testing Duplicate Validation ---")
    
    # 1. Create a dummy user
    email = "test_dup@example.com"
    username = "test_dup_user"
    if not CustomUser.objects.filter(email=email).exists():
        CustomUser.objects.create_user(username=username, email=email, password="password123")
        print(f"Created user: {username} ({email})")
    else:
        print(f"User already exists: {username} ({email})")

    # 2. Test CustomUserCreationForm (General User)
    print("\nTesting CustomUserCreationForm with duplicate email...")
    form_data = {
        'username': 'new_user_1', # unique
        'email': email,           # duplicate
        'birthday': '2000-01-01',
        'password': 'password123', # UserCreationForm needs passwords usually? 
        # Wait, UserCreationForm usually handles partial cleaning if fields are limited?
        # Actually UserCreationForm requires passwords. CustomUserCreationForm might inherit that.
    }
    # UserCreationForm expects password fields usually unless stripped?
    # Let's check the form definition again. it inherits UserCreationForm.
    # So we need validation to fail on EMAIL, not password missing.
    
    # We need to provide all required fields to isolate the email error.
    # But UserCreationForm handles password processing.
    # Let's see if we can just pass data without passwords if we only check `clean`.
    # But full_clean calls clean().
    
    # Adding passwords to be safe
    form_data['password'] = 'password123' 
    # UserCreationForm expects 'passwd1' and 'passwd2' usually? No, let's check field names.
    # Usually 'password' is not a field in ModelForm save, but processed.
    # Standard UserCreationForm has declared fields for passwords.
    
    # Let's instantiate and check errors.
    form = CustomUserCreationForm(data={
        'username': 'new_user_unique',
        'email': email,
        'birthday': '2000-01-01',
        # UserCreationForm fields are likely empty in Meta fields but declared in form.
    })
    
    # We need to simulate POST data including passwords if they are required.
    # UserCreationForm usually requires 'password_1' and 'password_2' or similar.
    # Let's check `UserCreationForm` source or behavior if possible, but standard is `password` and `password_confirm` often?
    # Django UserCreationForm uses 'username', 'password', 'password_confirmation' etc?
    # It uses 'username' and 'password' (2 fields).
    
    # Let's try validating.
    if not form.is_valid():
        # print(f"CustomUserCreationForm errors: {form.errors}")
        if 'email' in form.errors:
            print("[PASS] CustomUserCreationForm detected duplicate email.")
            print(f"Error message: {form.errors['email']}")
        else:
            print("[FAIL] CustomUserCreationForm did NOT detect duplicate email.")
            print(f"Errors: {form.errors.keys()}")
    else:
        print("[FAIL] CustomUserCreationForm passed validation with duplicate email.")

    # 3. Test StoreUserCreationForm (Store User)
    print("\nTesting StoreUserCreationForm with duplicate email...")
    store_form = StoreUserCreationForm(data={
        'username': 'new_store_unique',
        'email': email,
    })
    
    if not store_form.is_valid():
        # print(f"StoreUserCreationForm errors: {store_form.errors}")
        if 'email' in store_form.errors:
             print("[PASS] StoreUserCreationForm detected duplicate email.")
             print(f"Error message: {store_form.errors['email']}")
        else:
             print("[FAIL] StoreUserCreationForm did NOT detect duplicate email.")
             print(f"Errors: {store_form.errors.keys()}")
    else:
         print("[FAIL] StoreUserCreationForm passed validation with duplicate email.")

if __name__ == "__main__":
    test_duplicate_validation()
