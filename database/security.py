import hashlib
import secrets

def hash_password(password: str) -> str:
    """Hash password menggunakan PBKDF2 HMAC SHA-256 dengan random salt."""
    if password.startswith("pbkdf2:"):
        return password
    salt = secrets.token_hex(8)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"pbkdf2:{salt}:{hashed}"

def verify_password(plain: str, stored: str) -> bool:
    """Verifikasi password plain text terhadap stored hash (mendukung backward-compatibility)."""
    if not stored:
        return False
    if not stored.startswith("pbkdf2:"):
        # Backward compatibility untuk password lama plaintext
        return plain == stored
    parts = stored.split(":")
    if len(parts) != 3:
        return False
    _, salt, hashed = parts
    check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100000).hex()
    return secrets.compare_digest(check, hashed)
