import io
import math
import struct
import numpy as np
from PIL import Image
from typing import Tuple

_3D_EXTENSIONS = {"obj", "npy", "npz", "bin", "ply", "stl", "fbx", "glb"}


def is_3d_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in _3D_EXTENSIONS


def embed_in_3d(
    cover_bytes: bytes, secret_bytes: bytes, password: str, filename: str
) -> bytes:
    return _embed_binary(cover_bytes, secret_bytes, password)


def extract_from_3d(stego_bytes: bytes, password: str, filename: str) -> bytes:
    return _extract_binary(stego_bytes, password)


# --- Internal helpers ---


def _square_dims(n_bytes: int, is_embedded: bool = False) -> Tuple[int, int]:
    if is_embedded:
        side = int(math.sqrt(n_bytes // 3))
        return side, side
    side = math.ceil(math.sqrt(math.ceil(n_bytes / 3)))
    return max(128, side), max(128, side)


def _bytes_to_img(data: bytes, is_embedded: bool = False) -> Tuple[Image.Image, int]:
    arr = np.frombuffer(data, dtype=np.uint8).copy()
    H, W = _square_dims(len(arr), is_embedded)
    padded = np.zeros(H * W * 3, dtype=np.uint8)
    padded[: len(arr)] = arr
    return Image.fromarray(padded.reshape(H, W, 3), "RGB"), len(arr)


def _img_to_bytes(img: Image.Image, original_len: int) -> bytes:
    return bytes(np.array(img, dtype=np.uint8).flatten()[:original_len])


def _obj_to_array(content: str) -> Tuple[list, np.ndarray, list]:
    lines = content.split("\n")
    idx, vals = [], []
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("v ") or s.startswith("v\t"):
            parts = s.split()
            for j in range(1, min(len(parts), 5)):
                try:
                    idx.append((i, j))
                    vals.append(float(parts[j]))
                except ValueError:
                    pass
    return lines, np.array(vals, dtype=np.float64), idx


def _array_to_obj(lines: list, values: np.ndarray, idx: list) -> bytes:
    result = list(lines)
    for k, (i, j) in enumerate(idx):
        parts = result[i].split()
        parts[j] = f"{values[k]:.6f}"
        result[i] = " ".join(parts)
    return "\n".join(result).encode("utf-8")


def _embed_binary(cover_bytes: bytes, secret_bytes: bytes, password: str) -> bytes:
    from services.deep_stego_service import process_deep_encode
    from services.encryption import encrypt_data

    cipher = encrypt_data(secret_bytes, password)
    meta = b"META:" + struct.pack(">Q", len(cipher))

    side = 256
    canvas = np.ones(side * side * 3, dtype=np.uint8) * 128
    img = Image.fromarray(canvas.reshape(side, side, 3), "RGB")
    stego_img, _, _, _ = process_deep_encode(img, meta, password)
    stego_chunk = np.array(stego_img, dtype=np.uint8).flatten().tobytes()

    return cover_bytes + cipher + stego_chunk + struct.pack(">I", side) + b"STEGO"


def _extract_binary(stego_bytes: bytes, password: str) -> bytes:
    from services.deep_stego_service import process_deep_decode
    from services.encryption import decrypt_data

    if stego_bytes[-5:] != b"STEGO":
        raise ValueError(
            "This is not a valid stego file. Please upload the file downloaded from the app."
        )

    side = struct.unpack(">I", stego_bytes[-9:-5])[0]
    if not (128 <= side <= 8192):
        raise ValueError("Stego file metadata is corrupt.")

    chunk_size = side * side * 3
    chunk = stego_bytes[-9 - chunk_size : -9]
    img = Image.fromarray(
        np.frombuffer(chunk, dtype=np.uint8).reshape(side, side, 3), "RGB"
    )

    meta = process_deep_decode(img, password)
    if meta.startswith(b"META:"):
        cipher_len = struct.unpack(">Q", meta[5:13])[0]
        cipher = stego_bytes[-9 - chunk_size - cipher_len : -9 - chunk_size]
        return decrypt_data(cipher, password)

    return meta
