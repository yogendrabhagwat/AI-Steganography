import struct
import reedsolo

RS_NSYM = 32
BLOCK_SIZE = 200


def encode_ecc(data: bytes) -> bytes:
    rs = reedsolo.RSCodec(RS_NSYM)
    encoded_blocks = []
    for i in range(0, len(data), BLOCK_SIZE):
        block = data[i : i + BLOCK_SIZE]
        encoded_blocks.append(bytes(rs.encode(block)))
    header = struct.pack(">II", len(encoded_blocks), len(data))
    return header + b"".join(encoded_blocks)


def decode_ecc(data: bytes) -> bytes:
    if len(data) < 8:
        raise ValueError("ECC data too short.")
    num_blocks, original_len = struct.unpack(">II", data[:8])
    data = data[8:]
    rs = reedsolo.RSCodec(RS_NSYM)
    block_enc_size = BLOCK_SIZE + RS_NSYM
    decoded_parts = []
    for i in range(num_blocks):
        block = data[i * block_enc_size : (i + 1) * block_enc_size]
        if not block:
            break
        try:
            decoded_block, _, _ = rs.decode(block)
            decoded_parts.append(bytes(decoded_block))
        except reedsolo.ReedSolomonError:
            decoded_parts.append(b"\x00" * BLOCK_SIZE)
    result = b"".join(decoded_parts)
    return result[:original_len]
