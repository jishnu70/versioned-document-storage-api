# utils/hash_util.py

import hashlib

async def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
