import os
import sys
import django

# Add backend directory to sys.path
sys.path.insert(0, r"c:\Users\Abde\Desktop\attendance-system-QR (7)\attendance-system-QR\backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model, authenticate
from rest_framework.test import APIClient

User = get_user_model()

print("=" * 60)
print("INSPECTION DES UTILISATEURS EN BASE")
print("=" * 60)

users = User.objects.all().order_by("role", "email")
print(f"Total comptes trouvés: {users.count()}\n")

COMMON_PASSWORDS = [
    "Admin@123", "Admin@1234", "admin123", "admin", "password", "Password123",
    "Password@123", "12345678", "123456", "Abde@123", "Abde123", "Abder@123",
    "Secret123!", "passer123", "Azerty123", "Azerty@123"
]

client = APIClient()

account_results = []

for u in users:
    info = {
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "role": u.role,
        "is_active": u.is_active,
        "has_usable_password": u.has_usable_password(),
        "found_password": None,
        "login_api_status": None,
        "login_api_response": None
    }
    
    # Test common passwords
    for p in COMMON_PASSWORDS:
        if u.check_password(p):
            info["found_password"] = p
            break
            
    # Also test if password is their email or first name or role
    if not info["found_password"]:
        for extra in [u.email, u.first_name, u.last_name, u.role, u.email.split("@")[0]]:
            if extra and u.check_password(extra):
                info["found_password"] = extra
                break

    # If found password, test API /api/v1/users/login/
    if info["found_password"]:
        res = client.post("/api/v1/users/login/", {"email": u.email, "password": info["found_password"]}, format="json")
        info["login_api_status"] = res.status_code
        if res.status_code == 200:
            info["login_api_response"] = "SUCCESS (token received, role=" + res.data.get("user", {}).get("role", "") + ")"
        else:
            info["login_api_response"] = f"FAILED: {res.data}"

    account_results.append(info)

for acc in account_results:
    print(f"[{acc['role'].upper()}] {acc['email']}")
    print(f"  Nom: {acc['first_name']} {acc['last_name']}")
    print(f"  Actif: {acc['is_active']} | Has Usable Password: {acc['has_usable_password']}")
    if acc["found_password"]:
        print(f"  Mot de passe identifié: '{acc['found_password']}'")
        print(f"  Test API Login: HTTP {acc['login_api_status']} -> {acc['login_api_response']}")
    else:
        print(f"  Mot de passe: NON trouvé parmi les mots de passe standards courants")
    print("-" * 50)
