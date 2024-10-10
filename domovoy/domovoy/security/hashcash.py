import base64
import hashlib
import itertools
from datetime import timedelta, datetime

from ninja.security import APIKeyHeader

from django.utils import timezone
from django.conf import settings
from pydantic import BaseModel, Field

HASHCASH_SECRET = settings.SECRET_KEY
HASHCASH_VERSION = "1"
HASHCASH_DIFFICULTY = 4


def trailing_zeros(n):
    """Number of trailing 0s in binary representation of integer n."""
    if n <= 0: return 0
    for i in itertools.count(0):
        if n & (1 << i): return i

def irange(n):
    """Implementation of range(n) that does not overflow."""
    i = 0
    while i < n:
        yield i
        i += 1

def all_strings(charset='0123456789ABCDEF'):
    """Yields all strings in given character set, sorted by length."""
    m = len(charset)
    for n in itertools.count(0):
        for i in irange(m ** n):
            yield ''.join([charset[(i // (m ** j)) % m] for j in range(n)])

def hash(s):
    """Hash function used by hashcash. Returns an integer."""
    return int(hashlib.sha256(s).hexdigest(), 16)


def int_to_base64(n, length=8):
    byte_array = n.to_bytes(length, byteorder='big', signed=False)
    base64_encoded = base64.urlsafe_b64encode(byte_array)
    return base64_encoded.decode('utf-8').rstrip('=')


def sha256_b64_encode(data):
    sha256_hash = hashlib.sha256(data.encode()).digest()
    base64_encoded = base64.urlsafe_b64encode(sha256_hash)
    return base64_encoded.decode('utf-8').rstrip('=')


class HashcashConfig(BaseModel):
    version: int
    nonces: list[str]
    difficulty: int
    time: str = Field(description="Current time in format YYMMDDhhmm", examples=["2411301459"])

def get_hashcash_config(secret=HASHCASH_SECRET):
    nonce_times = [timezone.now(), timezone.now() - timedelta(hours=1)]
    nonce_values = [_.strftime("%y%m%d") + secret for _ in nonce_times]
    if nonce_values[0] == nonce_values[1]:
        nonce_values = nonce_values[:1]

    return {
        "version": HASHCASH_VERSION,
        "nonces": [sha256_b64_encode(_) for _ in nonce_values],
        "difficulty": HASHCASH_DIFFICULTY,
        "time": timezone.now().strftime("%y%m%d%H%M")
    }


def make_header(s, n, nonce, charset="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"):
    now = timezone.now().strftime("%y%m%d%H%M")
    base = f"{HASHCASH_VERSION}:{n}:{now}:{s}::{nonce}:".encode()
    for token in all_strings(charset):
        value = base + token.encode()
        if trailing_zeros(hash(value)) >= n:
            return value.decode()


def verify_header(header, secret=HASHCASH_SECRET):
    now = timezone.now()
    version, difficulty, raw_time, payload, ext, nonce, counter = header.split(":")
    if version != HASHCASH_VERSION:
        raise ValueError("Version does not match")
    if int(difficulty) < HASHCASH_DIFFICULTY:
        raise ValueError("Difficulty does not match")
    if nonce not in get_hashcash_config(secret)["nonces"]:
        raise ValueError("Unsupported nonce")
    time = timezone.make_aware(datetime.strptime(raw_time, "%y%m%d%H%M"))
    if abs((time - now).total_seconds()) > 60 * 60:
        raise ValueError("Time does not match")
    if trailing_zeros(hash(header.encode())) < HASHCASH_DIFFICULTY:
        raise ValueError("Hashcash not solved")
    return payload


class Hashcash(APIKeyHeader):
    param_name = "X-Hashcash"

    def authenticate(self, request, key):
        try:
            return verify_header(key)
        except (AttributeError, ValueError):
            return False
