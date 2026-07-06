import os
import sys
import requests
import time
import random
import math
import hashlib
import io
import threading
import struct
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# Set random seeds for reproducibility where needed
random.seed(42)

def clear_directory(path):
    if os.path.exists(path):
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    else:
        os.makedirs(path, exist_ok=True)

def parse_obj(content):
    vertices = []
    faces = []
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('v '):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                except ValueError:
                    pass
        elif line.startswith('f '):
            parts = line.split()
            face_indices = []
            for p in parts[1:]:
                v_idx = p.split('/')[0]
                try:
                    face_indices.append(int(v_idx))
                except ValueError:
                    pass
            if len(face_indices) >= 3:
                faces.append(face_indices)
    return vertices, faces

def normalize_vertices(vertices):
    if not vertices:
        return vertices
    min_x = min(v[0] for v in vertices)
    max_x = max(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)
    min_z = min(v[2] for v in vertices)
    max_z = max(v[2] for v in vertices)
    
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    cz = (min_z + max_z) / 2
    
    size_x = max_x - min_x
    size_y = max_y - min_y
    size_z = max_z - min_z
    max_size = max(size_x, size_y, size_z)
    if max_size == 0:
        max_size = 1.0
        
    normalized = []
    for v in vertices:
        nx = (v[0] - cx) / max_size
        ny = (v[1] - cy) / max_size
        nz = (v[2] - cz) / max_size
        normalized.append([nx, ny, nz])
    return normalized

def rotate_vertex(v, pitch, yaw, roll):
    x, y, z = v
    # pitch (X)
    cos_p, sin_p = math.cos(pitch), math.sin(pitch)
    y, z = y * cos_p - z * sin_p, y * sin_p + z * cos_p
    # yaw (Y)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
    # roll (Z)
    cos_r, sin_r = math.cos(roll), math.sin(roll)
    x, y = x * cos_r - y * sin_r, x * sin_r + y * cos_r
    return [x, y, z]

def transform_mesh(vertices, pitch, yaw, roll, scale, dx, dy, dz):
    transformed = []
    for v in vertices:
        rv = rotate_vertex(v, pitch, yaw, roll)
        sv = [rv[0] * scale, rv[1] * scale, rv[2] * scale]
        tv = [sv[0] + dx, sv[1] + dy, sv[2] + dz]
        transformed.append(tv)
    return transformed

def deform_mesh(vertices, intensity=0.1):
    verts = np.array(vertices, dtype=np.float32)
    deform_type = random.choice(['noise', 'twist', 'sine', 'taper', 'stretch'])
    
    if deform_type == 'noise':
        noise = np.random.normal(0, intensity * 0.1, size=verts.shape).astype(np.float32)
        verts += noise
    elif deform_type == 'twist':
        angle_factor = random.uniform(-1.0, 1.0)
        y = verts[:, 1]
        theta = y * angle_factor
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        x = verts[:, 0]
        z = verts[:, 2]
        verts[:, 0] = x * cos_t - z * sin_t
        verts[:, 2] = x * sin_t + z * cos_t
    elif deform_type == 'sine':
        freq = random.uniform(2.0, 4.0)
        amp = random.uniform(0.04, 0.08)
        y = verts[:, 1]
        verts[:, 0] += amp * np.sin(freq * y)
        verts[:, 2] += amp * np.cos(freq * y)
    elif deform_type == 'taper':
        factor = random.uniform(-0.4, 0.4)
        y = verts[:, 1]
        min_y, max_y = np.min(y), np.max(y)
        if max_y - min_y > 1e-5:
            ny = (y - min_y) / (max_y - min_y)
            scale = 1.0 + factor * ny
            verts[:, 0] *= scale
            verts[:, 2] *= scale
    elif deform_type == 'stretch':
        sx = random.uniform(0.75, 1.25)
        sy = random.uniform(0.75, 1.25)
        sz = random.uniform(0.75, 1.25)
        verts[:, 0] *= sx
        verts[:, 1] *= sy
        verts[:, 2] *= sz
        
    return verts.tolist()

def compute_normals(vertices, faces):
    verts = np.array(vertices, dtype=np.float32)
    v_normals = np.zeros_like(verts)
    f_normals = []
    
    for face in faces:
        i1, i2, i3 = face[0] - 1, face[1] - 1, face[2] - 1
        p1, p2, p3 = verts[i1], verts[i2], verts[i3]
        
        # Calculate face normal
        v_a = p2 - p1
        v_b = p3 - p1
        n = np.cross(v_a, v_b)
        n_len = np.linalg.norm(n)
        if n_len > 1e-6:
            n = n / n_len
        else:
            n = np.array([0.0, 0.0, 0.0], dtype=np.float32)
            
        f_normals.append(n)
        
        v_normals[i1] += n
        v_normals[i2] += n
        v_normals[i3] += n
        
    # Normalize vertex normals
    for i in range(len(v_normals)):
        n_len = np.linalg.norm(v_normals[i])
        if n_len > 1e-6:
            v_normals[i] = v_normals[i] / n_len
        else:
            v_normals[i] = np.array([0.0, 1.0, 0.0], dtype=np.float32)
            
    return v_normals.tolist(), [fn.tolist() for fn in f_normals]

def write_obj(filename, vertices, faces, vertex_normals, r, g, b):
    dirname = os.path.dirname(filename)
    basename = os.path.basename(filename)
    name_no_ext = os.path.splitext(basename)[0]
    mtl_filename = os.path.join(dirname, f"{name_no_ext}.mtl")
    
    # Write MTL file
    with open(mtl_filename, 'w') as fm:
        fm.write(f"# Material for {basename}\n")
        fm.write(f"newmtl Material_{name_no_ext}\n")
        fm.write(f"Kd {r:.4f} {g:.4f} {b:.4f}\n")
        fm.write("Ka 0.2 0.2 0.2\n")
        fm.write("Ks 0.5 0.5 0.5\n")
        fm.write("Ns 20.0\n")
        fm.write("d 1.0\n")
        fm.write("illum 2\n")

    # Write OBJ file
    with open(filename, 'w') as f:
        f.write(f"mtllib {name_no_ext}.mtl\n")
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for vn in vertex_normals:
            f.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")
        f.write(f"usemtl Material_{name_no_ext}\n")
        for face in faces:
            # Reference both vertex index and normal index (same value)
            face_str = " ".join(f"{idx}//{idx}" for idx in face)
            f.write(f"f {face_str}\n")

def write_ply(filename, vertices, faces, r, g, b):
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

def write_stl(filename, vertices, faces, face_normals):
    with open(filename, 'w', newline='\n') as f:
        f.write("solid Model\n")
        for i, face in enumerate(faces):
            v1 = vertices[face[0] - 1]
            v2 = vertices[face[1] - 1]
            v3 = vertices[face[2] - 1]
            fn = face_normals[i]
            f.write(f"  facet normal {fn[0]:.6f} {fn[1]:.6f} {fn[2]:.6f}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f}\n")
            f.write(f"      vertex {v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f}\n")
            f.write(f"      vertex {v3[0]:.6f} {v3[1]:.6f} {v3[2]:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid Model\n")

def write_npy(filename, vertices):
    arr = np.array(vertices, dtype=np.float32)
    np.save(filename, arr)

def write_npz(filename, vertices):
    arr = np.array(vertices, dtype=np.float32)
    np.savez(filename, vertices=arr)

def write_bin(filename, vertices):
    with open(filename, 'wb') as f:
        for v in vertices:
            f.write(struct.pack('<fff', v[0], v[1], v[2]))

def hsl_to_rgb(h, s, l):
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return r + m, g + m, b + m

def generate_sphere(radius=0.5, rings=20, sectors=20):
    vertices = []
    faces = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        for s in range(sectors):
            theta = 2 * math.pi * s / sectors
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            vertices.append([x, y, z])
    for r in range(rings):
        for s in range(sectors):
            v1 = r * sectors + s + 1
            v2 = r * sectors + (s + 1) % sectors + 1
            v3 = (r + 1) * sectors + (s + 1) % sectors + 1
            v4 = (r + 1) * sectors + s + 1
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    return vertices, faces

def generate_torus(r_tube=0.15, r_ring=0.4, rings=24, sectors=24):
    vertices = []
    faces = []
    for r in range(rings):
        phi = 2 * math.pi * r / rings
        for s in range(sectors):
            theta = 2 * math.pi * s / sectors
            x = (r_ring + r_tube * math.cos(theta)) * math.cos(phi)
            y = (r_ring + r_tube * math.cos(theta)) * math.sin(phi)
            z = r_tube * math.sin(theta)
            vertices.append([x, y, z])
    for r in range(rings):
        for s in range(sectors):
            r_next = (r + 1) % rings
            s_next = (s + 1) % sectors
            v1 = r * sectors + s + 1
            v2 = r * sectors + s_next + 1
            v3 = r_next * sectors + s_next + 1
            v4 = r_next * sectors + s + 1
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    return vertices, faces

def generate_apple(radius=0.45, rings=24, sectors=24):
    vertices = []
    faces = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        for s in range(sectors):
            theta = 2 * math.pi * s / sectors
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            
            # Dimple at poles
            r_xz = math.sqrt(x*x + z*z)
            if y > 0:
                y -= 0.08 * math.exp(-25.0 * (r_xz**2))
            else:
                y += 0.08 * math.exp(-25.0 * (r_xz**2))
                
            x *= 1.05
            z *= 1.05
            y *= 0.95
            vertices.append([x, y, z])
            
    for r in range(rings):
        for s in range(sectors):
            v1 = r * sectors + s + 1
            v2 = r * sectors + (s + 1) % sectors + 1
            v3 = (r + 1) * sectors + (s + 1) % sectors + 1
            v4 = (r + 1) * sectors + s + 1
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    return vertices, faces

def generate_pear(radius_factor=0.45, rings=24, sectors=24):
    vertices = []
    faces = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        y_norm = math.cos(phi)
        y = radius_factor * y_norm
        
        t = (1.0 - y_norm) / 2.0
        scale = 1.0 + 0.65 * math.sin(math.pi * t) * (0.3 + 0.7 * t)
        
        for s in range(sectors):
            theta = 2 * math.pi * s / sectors
            x = radius_factor * math.sin(phi) * math.cos(theta) * scale
            z = radius_factor * math.sin(phi) * math.sin(theta) * scale
            vertices.append([x, y, z])
            
    for r in range(rings):
        for s in range(sectors):
            v1 = r * sectors + s + 1
            v2 = r * sectors + (s + 1) % sectors + 1
            v3 = (r + 1) * sectors + (s + 1) % sectors + 1
            v4 = (r + 1) * sectors + s + 1
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    return vertices, faces

def generate_banana(length=0.9, rings=20, sectors=6):
    vertices = []
    faces = []
    for r in range(rings + 1):
        t = (r / rings) - 0.5
        cx = 0.18 * math.cos(math.pi * t)
        cy = length * t
        cz = 0.0
        rad = 0.14 * math.cos(math.pi * t)
        if rad < 0.01:
            rad = 0.01
            
        for s in range(sectors):
            theta = 2 * math.pi * s / sectors
            x = cx + rad * math.cos(theta)
            z = cz + rad * math.sin(theta)
            vertices.append([x, cy, z])
            
    for r in range(rings):
        for s in range(sectors):
            v1 = r * sectors + s + 1
            v2 = r * sectors + (s + 1) % sectors + 1
            v3 = (r + 1) * sectors + (s + 1) % sectors + 1
            v4 = (r + 1) * sectors + s + 1
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    return vertices, faces

def generate_orange(radius=0.45, rings=24, sectors=24):
    vertices = []
    faces = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        for s in range(sectors):
            theta = 2 * math.pi * s / sectors
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            
            noise = 0.006 * math.sin(10 * theta) * math.cos(10 * phi)
            x += noise * math.sin(phi) * math.cos(theta)
            y += noise * math.cos(phi)
            z += noise * math.sin(phi) * math.sin(theta)
            
            vertices.append([x, y, z])
            
    for r in range(rings):
        for s in range(sectors):
            v1 = r * sectors + s + 1
            v2 = r * sectors + (s + 1) % sectors + 1
            v3 = (r + 1) * sectors + (s + 1) % sectors + 1
            v4 = (r + 1) * sectors + s + 1
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    return vertices, faces

def download_with_retry(name, url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                vertices, faces = parse_obj(r.text)
                if len(vertices) > 0 and len(faces) > 0:
                    return vertices, faces
            print(f"Attempt {attempt+1} failed for download {name}, retrying...")
            time.sleep(1)
        except Exception as e:
            print(f"Attempt {attempt+1} failed for download {name} with error: {e}, retrying...")
            time.sleep(1)
    return None, None

def load_local_mesh(path):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
            verts, faces = parse_obj(content)
            if len(verts) > 0 and len(faces) > 0:
                return verts, faces
    except Exception as e:
        print(f"Error loading local mesh {path}: {e}")
    return None, None

def main():
    print("=== Steganography Mixed Realistic Dataset Generator ===")
    
    img_dir = os.path.join("dataset", "2d img")
    model_dir = os.path.join("dataset", "3d img")
    
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    
    # 1. Clean 3D models directory
    print("Clearing 3D models target directory...")
    clear_directory(model_dir)
    
    # 2. Load base 3D meshes (with caching and downloading)
    base_meshes = {}
    
    models_to_load = {
        "bunny": ("unnecessary_backup/model_004.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/bunny.obj"),
        "teapot": ("unnecessary_backup/model_003.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/teapot.obj"),
        "suzanne": ("unnecessary_backup/suzanne.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/suzanne.obj"),
        "spot": ("unnecessary_backup/model_007.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/spot.obj"),
        "cow": ("unnecessary_backup/cow.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/cow.obj"),
        "horse": ("unnecessary_backup/horse.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/horse.obj"),
        "armadillo": ("unnecessary_backup/armadillo.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/armadillo.obj"),
        "cheburashka": ("unnecessary_backup/cheburashka.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/cheburashka.obj"),
        "homer": ("unnecessary_backup/homer.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/homer.obj"),
        "woody": ("unnecessary_backup/woody.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/woody.obj"),
        "fandisk": ("unnecessary_backup/fandisk.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/fandisk.obj"),
        "beetle": ("unnecessary_backup/beetle.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/beetle.obj"),
        "alligator": ("unnecessary_backup/alligator.obj", "https://raw.githubusercontent.com/alecjacobson/common-3d-test-models/master/data/alligator.obj"),
    }
    
    os.makedirs("unnecessary_backup", exist_ok=True)
    
    for name, (local_path, url) in models_to_load.items():
        verts, faces = None, None
        if os.path.exists(local_path):
            print(f"Loading local {name} model from cache...")
            verts, faces = load_local_mesh(local_path)
            
        if not verts:
            print(f"Fetching {name} model from github...")
            verts, faces = download_with_retry(name, url)
            if verts and faces:
                try:
                    # Cache it locally to avoid redownloads
                    with open(local_path, 'w') as fcache:
                        for v in verts:
                            fcache.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                        for face in faces:
                            fcache.write(f"f {' '.join(str(idx) for idx in face)}\n")
                    print(f"Cached {name} locally.")
                except Exception as e:
                    print(f"Failed to cache {name}: {e}")
                    
        if verts and faces:
            base_meshes[name] = (normalize_vertices(verts), faces)
            print(f"Loaded {name} successfully.")
        else:
            print(f"Warning: Could not load/download {name}.")
            
    # Generate procedural fruits and torus/donut
    print("Generating procedural shapes (fruits/donut)...")
    
    try:
        ap_verts, ap_faces = generate_apple()
        base_meshes["apple"] = (normalize_vertices(ap_verts), ap_faces)
        print("Generated Apple successfully.")
    except Exception as e:
        print(f"Failed to generate Apple: {e}")
        
    try:
        pr_verts, pr_faces = generate_pear()
        base_meshes["pear"] = (normalize_vertices(pr_verts), pr_faces)
        print("Generated Pear successfully.")
    except Exception as e:
        print(f"Failed to generate Pear: {e}")
        
    try:
        ba_verts, ba_faces = generate_banana()
        base_meshes["banana"] = (normalize_vertices(ba_verts), ba_faces)
        print("Generated Banana successfully.")
    except Exception as e:
        print(f"Failed to generate Banana: {e}")
        
    try:
        or_verts, or_faces = generate_orange()
        base_meshes["orange"] = (normalize_vertices(or_verts), or_faces)
        print("Generated Orange successfully.")
    except Exception as e:
        print(f"Failed to generate Orange: {e}")
        
    try:
        tr_verts, tr_faces = generate_torus()
        base_meshes["donut"] = (normalize_vertices(tr_verts), tr_faces)
        print("Generated Donut (Torus) successfully.")
    except Exception as e:
        print(f"Failed to generate Donut: {e}")
        
    # 3. Generate 1,000 unique 3D meshes in diverse formats
    print("\nGenerating 1,000 unique realistic 3D models in diverse formats...")
    mesh_names = list(base_meshes.keys())
    
    for i in range(1, 1001):
        mesh_type = random.choice(mesh_names)
        verts, faces = base_meshes[mesh_type]
        
        # Apply random shape deformations (makes each of the 1000 models distinct)
        deformed_verts = deform_mesh(verts, intensity=0.12)
        
        # Apply random transformations
        pitch = random.uniform(0, 2 * math.pi)
        yaw = random.uniform(0, 2 * math.pi)
        roll = random.uniform(0, 2 * math.pi)
        scale = random.uniform(0.7, 1.3)
        dx = random.uniform(-0.1, 0.1)
        dy = random.uniform(-0.1, 0.1)
        dz = random.uniform(-0.1, 0.1)
        
        trans_verts = transform_mesh(deformed_verts, pitch, yaw, roll, scale, dx, dy, dz)
        
        # Generate color in HSL for maximum vibrancy
        h = random.uniform(0, 360)
        s = 0.95
        l = 0.5
        r, g, b = hsl_to_rgb(h, s, l)
        
        # Distribute formats across indices
        if i <= 200:
            # OBJ format (200 files)
            obj_file = os.path.join(model_dir, f"model_{i:04d}.obj")
            v_norms, f_norms = compute_normals(trans_verts, faces)
            write_obj(obj_file, trans_verts, faces, v_norms, r, g, b)
        elif i <= 400:
            # PLY format (200 files)
            ply_file = os.path.join(model_dir, f"model_{i:04d}.ply")
            write_ply(ply_file, trans_verts, faces, r, g, b)
        elif i <= 600:
            # STL format (200 files)
            stl_file = os.path.join(model_dir, f"model_{i:04d}.stl")
            v_norms, f_norms = compute_normals(trans_verts, faces)
            write_stl(stl_file, trans_verts, faces, f_norms)
        elif i <= 700:
            # NPY format (100 files)
            npy_file = os.path.join(model_dir, f"model_{i:04d}.npy")
            write_npy(npy_file, trans_verts)
        elif i <= 800:
            # NPZ format (100 files)
            npz_file = os.path.join(model_dir, f"model_{i:04d}.npz")
            write_npz(npz_file, trans_verts)
        else:
            # BIN format (200 files)
            bin_file = os.path.join(model_dir, f"model_{i:04d}.bin")
            write_bin(bin_file, trans_verts)
            
        if i % 100 == 0:
            print(f"Generated {i}/1000 3D models...")
            
    print("3D models generated successfully!")
    
    # 4. Check if 2D Images already exist to avoid redownloading
    existing_images = []
    if os.path.exists(img_dir):
        existing_images = [f for f in os.listdir(img_dir) if f.startswith("img_") and f.endswith(".jpg")]
        
    if len(existing_images) == 1000:
        print("\nFound 1,000 existing 2D images. Skipping image download.")
    else:
        print(f"\nDownloading 1,000 unique 1024x1024 photographic images concurrently...")
        clear_directory(img_dir)
        seen_hashes = set()
        hashes_lock = threading.Lock()
        
        futures = {}
        seed_counter = 1
        completed_count = 0
        count = 1000
        
        with ThreadPoolExecutor(max_workers=45) as executor:
            # Submit initial batch
            for idx in range(1, count + 1):
                url = f"https://picsum.photos/1024/1024?random={seed_counter}"
                futures[executor.submit(requests.get, url, timeout=20)] = (idx, seed_counter)
                seed_counter += 1
                
            while completed_count < count:
                for future in list(futures.keys()):
                    if future.done():
                        idx_to_save, seed = futures.pop(future)
                        try:
                            response = future.result()
                            if response.status_code == 200:
                                content = response.content
                                md5_hash = hashlib.md5(content).hexdigest()
                                
                                is_duplicate = False
                                with hashes_lock:
                                    if md5_hash in seen_hashes:
                                        is_duplicate = True
                                    else:
                                        seen_hashes.add(md5_hash)
                                        
                                if is_duplicate:
                                    # Resubmit a request with a new seed
                                    url = f"https://picsum.photos/1024/1024?random={seed_counter}"
                                    futures[executor.submit(requests.get, url, timeout=20)] = (idx_to_save, seed_counter)
                                    seed_counter += 1
                                    continue
                                    
                                # Verify image
                                try:
                                    img = Image.open(io.BytesIO(content))
                                    img.verify()
                                except Exception:
                                    # Resubmit if corrupted
                                    url = f"https://picsum.photos/1024/1024?random={seed_counter}"
                                    futures[executor.submit(requests.get, url, timeout=20)] = (idx_to_save, seed_counter)
                                    seed_counter += 1
                                    continue
                                    
                                # Save valid, unique image
                                filename = os.path.join(img_dir, f"img_{idx_to_save:04d}.jpg")
                                with open(filename, 'wb') as f:
                                    f.write(content)
                                    
                                completed_count += 1
                                if completed_count % 100 == 0 or completed_count == count:
                                    print(f"Downloaded {completed_count}/{count} unique images...")
                            else:
                                # Resubmit on bad status
                                url = f"https://picsum.photos/1024/1024?random={seed_counter}"
                                futures[executor.submit(requests.get, url, timeout=20)] = (idx_to_save, seed_counter)
                                seed_counter += 1
                        except Exception:
                            # Resubmit on exception (timeout/network error)
                            url = f"https://picsum.photos/1024/1024?random={seed_counter}"
                            futures[executor.submit(requests.get, url, timeout=20)] = (idx_to_save, seed_counter)
                            seed_counter += 1
                time.sleep(0.05)
                
    print("\nDataset creation complete!")
    print(f"2D images in: {img_dir} (1000 files, unique, 1024x1024)")
    print(f"3D models in: {model_dir} (1000 files in diverse formats: OBJ, PLY, STL, NPY, NPZ, BIN)")

if __name__ == '__main__':
    main()
