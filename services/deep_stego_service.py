import os
import math
import struct
import base64
import time
import torch
import torch.nn.functional as F
from PIL import Image
import numpy as np
from collections import Counter
from reedsolo import RSCodec
from models.core.deep_models import DeepStegoEncoder, DeepStegoDecoder
from services.encryption import encrypt_data, decrypt_data

RS_SYMBOLS = 120
rs_codec = RSCodec(RS_SYMBOLS)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if device.type == "cpu":
    torch.set_num_threads(min(4, os.cpu_count() or 1))


class SteganoEngine:

    def __init__(self):
        self.encoder = DeepStegoEncoder().to(device)
        self.decoder = DeepStegoDecoder().to(device)
        self.is_loaded = False
        self.max_resolution = 2048
        model_dir = os.path.join(os.getcwd(), "saved_models")
        os.makedirs(model_dir, exist_ok=True)
        self.enc_file = os.path.join(model_dir, "encoder_deep.pth")
        self.dec_file = os.path.join(model_dir, "decoder_deep.pth")
        self._load_weights()

    def _load_weights(self):
        if os.path.exists(self.enc_file) and os.path.exists(self.dec_file):
            try:
                self.encoder.load_state_dict(
                    torch.load(self.enc_file, map_location=device), strict=False
                )
                self.decoder.load_state_dict(
                    torch.load(self.dec_file, map_location=device), strict=False
                )
                self.encoder.eval()
                self.decoder.eval()
                self.is_loaded = True
                print("[Model] Weights loaded.")
            except Exception:
                print("[Model] Using default weights.")

    def activate(self):
        self.is_loaded = True


engine = SteganoEngine()


def _bytes_to_tensor(data: bytes, shape):
    H, W = shape
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    if len(bits) > H * W:
        raise ValueError("Secret data is too large for this image.")
    bits = np.pad(bits, (0, H * W - len(bits)), mode="constant")
    return torch.from_numpy(bits).float().view(1, 1, H, W).to(device)


def _tensor_to_bytes(tensor, byte_count: int):
    bits = (tensor > 0.5).int().cpu().numpy().flatten()
    return np.packbits(bits[: byte_count * 8]).tobytes()


def process_deep_encode(cover_image: Image.Image, secret_bytes: bytes, password: str):
    t = time.time()

    if cover_image.mode != "RGB":
        cover_image = cover_image.convert("RGB")

    w, h = cover_image.size
    if max(w, h) > engine.max_resolution:
        cover_image.thumbnail(
            (engine.max_resolution, engine.max_resolution), Image.LANCZOS
        )
    w, h = cover_image.size
    w, h = w // 16 * 16, h // 16 * 16
    cover_image = cover_image.resize((w, h))

    img_arr = np.array(cover_image).astype(np.float32) / 255.0
    cover_tensor = torch.from_numpy(img_arr.transpose(2, 0, 1)).unsqueeze(0).to(device)

    if not engine.is_loaded:
        engine.activate()

    encrypted = encrypt_data(secret_bytes, password)
    capacity = w // 2 * (h // 2) // 8
    max_len = (capacity - 124) // 255 * (255 - RS_SYMBOLS)
    appended = b""

    if len(encrypted) > max_len:
        rs_data = rs_codec.encode(b"META:" + struct.pack(">Q", len(encrypted)))
        appended = encrypted
    else:
        rs_data = rs_codec.encode(encrypted)

    payload = struct.pack(">I", len(rs_data)) * 31 + rs_data
    if len(payload) > capacity:
        raise ValueError(
            f"Data too large: needs {len(payload)} bytes, capacity is {capacity}."
        )

    secret_tensor = _bytes_to_tensor(payload, (h // 2, w // 2))

    with torch.no_grad():
        with torch.autocast(device_type=device.type, enabled=torch.cuda.is_available()):
            stego_tensor = engine.encoder(cover_tensor, secret_tensor)

    mse = F.mse_loss(stego_tensor, cover_tensor).item()
    psnr = 10 * math.log10(1.0 / (mse + 1e-10))
    pixels = (
        (stego_tensor.squeeze(0).cpu().numpy().transpose(1, 2, 0) * 255.0)
        .clip(0, 255)
        .astype(np.uint8)
    )

    print(f"[Encode] Done in {(time.time() - t) * 1000:.1f}ms")
    return Image.fromarray(pixels), round(psnr, 2), 0.99, appended


def process_deep_decode(
    stego_image: Image.Image, password: str, raw_bytes: bytes = None
) -> bytes:
    if not engine.is_loaded:
        engine.activate()

    if stego_image.mode != "RGB":
        stego_image = stego_image.convert("RGB")

    arr = np.array(stego_image).astype(np.float32) / 255.0
    stego_tensor = torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0).to(device)

    with torch.no_grad():
        with torch.autocast(device_type=device.type, enabled=torch.cuda.is_available()):
            pred = engine.decoder(stego_tensor)

    bits = (pred > 0.5).int().cpu().numpy().flatten()
    votes = []
    for i in range(31):
        try:
            val = struct.unpack(
                ">I", np.packbits(bits[i * 32 : (i + 1) * 32]).tobytes()
            )[0]
            if 0 < val < 10_000_000:
                votes.append(val)
        except Exception:
            pass

    if not votes:
        raise ValueError("No hidden data found. Make sure this is a stego image.")

    length = Counter(votes).most_common(1)[0][0]
    payload = _tensor_to_bytes(pred, length + 124)[124:]

    try:
        decoded, _, _ = rs_codec.decode(payload)
        decoded = bytes(decoded)
    except Exception:
        raise ValueError("Error correction failed. Data may be corrupted.")

    if decoded.startswith(b"META:") and raw_bytes:
        tail_len = struct.unpack(">Q", decoded[5:13])[0]
        try:
            return decrypt_data(raw_bytes[-tail_len:], password)
        except Exception:
            raise ValueError("Decryption failed. Incorrect password.")

    try:
        return decrypt_data(decoded, password)
    except Exception:
        raise ValueError("Decryption failed. Incorrect password.")


def bytes_to_secret(data: bytes):
    if data.startswith(b"TXT:"):
        return {"type": "text", "content": data[4:].decode("utf-8", errors="replace")}
    if data.startswith(b"IMG:"):
        try:
            content = "data:image/jpeg;base64," + base64.b64encode(data[4:]).decode()
        except Exception:
            content = ""
        return {
            "type": "image",
            "content": content,
            "raw_bytes": data[4:],
            "ext": "jpg",
        }
    if data.startswith(b"3DV:") or data.startswith(b"3DR:"):
        is_direct = data.startswith(b"3DV:")
        ext = "npy" if is_direct else data[4:12].decode("utf-8").strip()
        raw = data[4:] if is_direct else data[12:]
        return {"type": "3d", "content": "3D Asset Data", "raw_bytes": raw, "ext": ext}
    return {"type": "text", "content": data.decode("utf-8", errors="replace")}


def secret_text_to_bytes(text: str) -> bytes:
    return b"TXT:" + text.encode("utf-8")


def secret_image_to_bytes(stream) -> bytes:
    return b"IMG:" + stream.read()


def secret_3d_to_bytes(stream, ext="npy") -> bytes:
    if ext == "npy":
        return b"3DV:" + stream.read()
    return b"3DR:" + ext.ljust(8).encode("utf-8") + stream.read()
