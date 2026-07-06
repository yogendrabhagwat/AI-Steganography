from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
import hashlib

_EMBED_SALT = b"stegano_embed_v1_salt_fixed_2024"


def encrypt_data(plaintext: bytes, password: str) -> bytes:
    salt = get_random_bytes(16)
    key = PBKDF2(password.encode("utf-8"), salt, dkLen=32, count=200000)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return salt + cipher.nonce + tag + ciphertext


def decrypt_data(data: bytes, password: str) -> bytes:
    if len(data) < 48:
        raise ValueError("The provided data is too small to be a valid cryptogram.")
    salt = data[:16]
    nonce = data[16:32]
    tag = data[32:48]
    ciphertext = data[48:]
    key = PBKDF2(password.encode("utf-8"), salt, dkLen=32, count=200000)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        return cipher.decrypt_and_verify(ciphertext, tag)
    except Exception:
        raise ValueError("Decryption failed. Please check your password or file.")


def derive_embedding_key(password: str) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), _EMBED_SALT, iterations=50000, dklen=32
    )
