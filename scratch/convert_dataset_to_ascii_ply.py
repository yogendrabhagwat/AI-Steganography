import os
import sys

def parse_obj(content):
    vertices, faces = [], []
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('v '):
            parts = line.split()
            if len(parts) >= 4:
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif line.startswith('f '):
            parts = line.split()
            face_indices = []
            for p in parts[1:]:
                face_indices.append(int(p.split('/')[0]))
            if len(face_indices) >= 3:
                faces.append(face_indices)
    return vertices, faces

def parse_mtl_color(content):
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('Kd '):
            parts = line.split()
            if len(parts) >= 4:
                return float(parts[1]), float(parts[2]), float(parts[3])
    return 0.5, 0.5, 0.5

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
            # OBJ is 1-indexed, PLY is 0-indexed
            indices_str = " ".join(str(idx - 1) for idx in face)
            f.write(f"{len(face)} {indices_str}\n")

def main():
    model_dir = "dataset/3d img"
    if not os.path.exists(model_dir):
        print(f"Error: Directory {model_dir} does not exist.")
        sys.exit(1)
        
    converted = 0
    for i in range(1, 1001):
        obj_name = f"model_{i:04d}.obj"
        mtl_name = f"model_{i:04d}.mtl"
        ply_name = f"model_{i:04d}.ply"
        
        obj_path = os.path.join(model_dir, obj_name)
        mtl_path = os.path.join(model_dir, mtl_name)
        ply_path = os.path.join(model_dir, ply_name)
        
        if not os.path.exists(obj_path) or not os.path.exists(mtl_path):
            print(f"Warning: Missing OBJ or MTL for index {i}, skipping.")
            continue
            
        with open(obj_path, 'r') as f:
            obj_content = f.read()
        with open(mtl_path, 'r') as f:
            mtl_content = f.read()
            
        vertices, faces = parse_obj(obj_content)
        r, g, b = parse_mtl_color(mtl_content)
        
        write_ascii_ply(ply_path, vertices, faces, r, g, b)
        converted += 1
        
        if converted % 100 == 0:
            print(f"Converted {converted}/1000 models to ASCII PLY...")

    print(f"Successfully converted {converted} models to ASCII PLY format.")

if __name__ == '__main__':
    main()
