from cryptography.fernet import Fernet

key = b'S0mr0OZC7gAAIPz7RFsbqtKXF5Vz7LfODHAjeJYcDEc='


def encode_text(text: str) -> str:
    refKey = Fernet(key)
    return refKey.encrypt(bytes(text, "utf-8")).decode("utf-8")


def decode_text(encoded_text: str) -> str:
    refKey = Fernet(key)
    return refKey.decrypt(bytes(encoded_text, "utf-8")).decode("utf-8")
