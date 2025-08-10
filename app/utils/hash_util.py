# utils/hash_util.py

import hashlib

def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
