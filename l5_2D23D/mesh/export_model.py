"""Export mesh to multiple formats: PLY, OBJ, GLB.

GLB is constructed manually following the glTF 2.0 binary specification
since both Open3D's ASSIMP-based writer and pygltflib's convert_buffers
can produce broken buffer views for the triangle indices.
"""

import json
import os
import struct
import numpy as np
import open3d as o3d


def export_ply(mesh, output_path):
    o3d.io.write_triangle_mesh(output_path, mesh)
    return os.path.exists(output_path)


def export_obj(mesh, output_path):
    o3d.io.write_triangle_mesh(output_path, mesh)
    return os.path.exists(output_path)


def _write_glb(verts, tris, colors, normals, output_path):
    """Write a glTF 2.0 binary (.glb) file from mesh geometry arrays.

    All arrays are float32.  colors is (N,4) or None; normals is (N,3) or None.
    """
    n_verts = len(verts)
    n_tris = len(tris)

    # Determine index storage
    max_idx = tris.max() if n_tris > 0 else 0
    use_ushort = max_idx < 65535
    index_component_type = 5123 if use_ushort else 5125  # UNSIGNED_SHORT : UNSIGNED_INT
    idx_dtype = np.uint16 if use_ushort else np.uint32
    idx_bytes = tris.astype(idx_dtype).tobytes()

    # --- Build binary buffer: positions | normals | colors | indices ---
    buf = bytearray()
    pad = lambda b: b + b'\x00' * ((4 - len(b) % 4) % 4)

    pos_bytes = verts.astype(np.float32).tobytes()
    pos_offset = 0
    buf.extend(pos_bytes)

    normal_offset = len(buf)
    has_normals = normals is not None and len(normals) == n_verts
    if has_normals:
        buf.extend(normals.astype(np.float32).tobytes())

    color_offset = len(buf)
    has_colors = colors is not None and len(colors) == n_verts
    if has_colors:
        buf.extend(colors.astype(np.float32).tobytes())

    idx_offset = len(buf)
    buf.extend(idx_bytes)

    # Pad buffer to 4 bytes
    while len(buf) % 4 != 0:
        buf.append(0)

    # --- Build accessors and bufferViews ---
    accessors = []
    bufferViews = []

    # POSITION accessor (0) + bufferView (0)
    pos_min = verts.min(axis=0).tolist()
    pos_max = verts.max(axis=0).tolist()
    accessors.append({
        "bufferView": 0, "componentType": 5126, "count": n_verts,
        "type": "VEC3", "min": pos_min, "max": pos_max,
        "byteOffset": 0
    })
    bufferViews.append({
        "buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes),
        "target": 34962
    })

    bv_idx = 1

    # NORMAL accessor + bufferView
    if has_normals:
        accessors.append({
            "bufferView": bv_idx, "componentType": 5126, "count": n_verts,
            "type": "VEC3", "byteOffset": 0
        })
        bufferViews.append({
            "buffer": 0, "byteOffset": normal_offset,
            "byteLength": n_verts * 3 * 4, "target": 34962
        })
        bv_idx += 1

    # COLOR_0 accessor + bufferView
    if has_colors:
        accessors.append({
            "bufferView": bv_idx, "componentType": 5126, "count": n_verts,
            "type": "VEC4", "byteOffset": 0
        })
        bufferViews.append({
            "buffer": 0, "byteOffset": color_offset,
            "byteLength": n_verts * 4 * 4, "target": 34962
        })
        bv_idx += 1

    # INDEX accessor + bufferView
    accessors.append({
        "bufferView": bv_idx, "componentType": index_component_type,
        "count": n_tris * 3, "type": "SCALAR",
        "min": [int(tris.min())], "max": [int(tris.max())],
        "byteOffset": 0
    })
    bufferViews.append({
        "buffer": 0, "byteOffset": idx_offset,
        "byteLength": len(idx_bytes), "target": 34963
    })

    # --- Build primitive attributes ---
    attrs = {"POSITION": 0}
    acc_idx = 1
    if has_normals:
        attrs["NORMAL"] = acc_idx
        acc_idx += 1
    if has_colors:
        attrs["COLOR_0"] = acc_idx
        acc_idx += 1

    # --- Assemble glTF JSON ---
    gltf_json = {
        "asset": {"version": "2.0", "generator": "hand-rolled-glb"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": attrs, "indices": acc_idx}]}],
        "accessors": accessors,
        "bufferViews": bufferViews,
        "buffers": [{"byteLength": len(buf)}],
    }

    json_str = json.dumps(gltf_json, separators=(',', ':'), allow_nan=False)
    json_bytes = json_str.encode("utf-8")

    # Pad JSON chunk to 4 bytes with spaces (valid JSON whitespace)
    while len(json_bytes) % 4 != 0:
        json_bytes += b' '

    # --- Write GLB ---
    # Header: magic(4) + version(4 LE) + total_length(4 LE)
    # JSON chunk: json_length(4 LE) + json_type(4 = 0x4E4F534A) + json_data
    # BIN chunk:  bin_length(4 LE)  + bin_type(4  = 0x004E4942) + bin_data

    json_chunk_len = len(json_bytes)
    bin_chunk_len = len(buf)
    header_len = 12
    chunk_header_len = 8
    total_len = header_len + chunk_header_len + json_chunk_len + chunk_header_len + bin_chunk_len

    with open(output_path, "wb") as f:
        # Header
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        # JSON chunk
        f.write(struct.pack("<I", json_chunk_len))
        f.write(struct.pack("<I", 0x4E4F534A))  # 'JSON' in little-endian
        f.write(json_bytes)
        # BIN chunk
        f.write(struct.pack("<I", bin_chunk_len))
        f.write(struct.pack("<I", 0x004E4942))  # 'BIN\0' in little-endian
        f.write(buf)

    return True


def export_glb(mesh, output_path):
    """Export mesh as valid GLB using manual binary construction."""
    verts = np.asarray(mesh.vertices, dtype=np.float32)
    tris = np.asarray(mesh.triangles, dtype=np.uint32)

    colors = None
    if mesh.has_vertex_colors():
        colors = np.asarray(mesh.vertex_colors, dtype=np.float32)

    normals = None
    if mesh.has_vertex_normals():
        normals = np.asarray(mesh.vertex_normals, dtype=np.float32)

    return _write_glb(verts, tris, colors, normals, output_path)


def export_all(mesh, results_dir):
    """Export mesh to PLY, OBJ, and GLB formats."""
    mesh_dir = os.path.join(results_dir, "mesh")
    os.makedirs(mesh_dir, exist_ok=True)

    results = {}

    ply_path = os.path.join(mesh_dir, "model.ply")
    results["ply"] = export_ply(mesh, ply_path)

    obj_path = os.path.join(mesh_dir, "model.obj")
    results["obj"] = export_obj(mesh, obj_path)

    glb_path = os.path.join(mesh_dir, "model.glb")
    results["glb"] = export_glb(mesh, glb_path)

    return results
