import os
import struct
import math
import sys

def write_ascii_ply(filename, vertices, faces, r, g, b):
    ir = int(r * 255)
    ig = int(g * 255)
    ib = int(b * 255)
    header = (
        "ply\n"
        "format ascii 1.0\n"
        "comment Created by Antigravity\n"
        f"element vertex {len(vertices)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        f"element face {len(faces)}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    )
    with open(filename, 'w', newline='\n') as f:
        f.write(header)
        for v in vertices:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {ir} {ig} {ib}\n")
        for face in faces:
            indices_str = " ".join(str(idx - 1) for idx in face)
            f.write(f"{len(face)} {indices_str}\n")

def write_binary_ply(filename, vertices, faces, r, g, b):
    ir = int(r * 255)
    ig = int(g * 255)
    ib = int(b * 255)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "comment Created by Antigravity\n"
        f"element vertex {len(vertices)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        f"element face {len(faces)}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    )
    with open(filename, 'wb') as f:
        f.write(header.encode('ascii'))
        for v in vertices:
            f.write(struct.pack("<fffBBB", v[0], v[1], v[2], ir, ig, ib))
        for face in faces:
            f.write(struct.pack("<B", len(face)))
            f.write(struct.pack(f"<{len(face)}i", *(idx - 1 for idx in face)))

# Create simple tetrahedron
vertices = [
    [0.0, 1.0, 0.0],
    [-0.94, -0.33, -0.54],
    [0.94, -0.33, -0.54],
    [0.0, -0.33, 1.0]
]
faces = [
    [1, 2, 3],
    [1, 3, 4],
    [1, 4, 2],
    [2, 4, 3]
]

os.makedirs("scratch/test_models", exist_ok=True)
write_ascii_ply("scratch/test_models/tetra_ascii.ply", vertices, faces, 1.0, 0.0, 0.0)
write_binary_ply("scratch/test_models/tetra_binary.ply", vertices, faces, 1.0, 0.0, 0.0)
print("ASCII and Binary tetrahedron models written.")
