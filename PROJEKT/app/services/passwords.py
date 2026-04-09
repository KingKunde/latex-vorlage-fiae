from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        return password_hasher.verify(stored_password_hash, password)
    except (InvalidHashError, VerifyMismatchError, VerificationError):
        return stored_password_hash == password


def validate_password_strength(password: str) -> str | None:
    if len(password) < 12:
        return "Passwort muss mindestens 12 Zeichen lang sein."
    if password.lower() == password or password.upper() == password:
        return "Passwort muss Groß- und Kleinbuchstaben enthalten."
    if not any(character.isdigit() for character in password):
        return "Passwort muss mindestens eine Zahl enthalten."
    if not any(not character.isalnum() for character in password):
        return "Passwort muss mindestens ein Sonderzeichen enthalten."
    return None
