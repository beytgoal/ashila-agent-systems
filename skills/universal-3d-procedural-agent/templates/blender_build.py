#!/usr/bin/env python3
"""
blender_build.py — Universal 3D Procedural Production Agent, TAHAP 1.
Spec-driven procedural modeller: reads a JSON spec describing an object as
components built from primitives, builds it in Blender, UV-unwraps every
mesh, assigns dynamic materials, exports ONE .glb file.

Usage (headless):
    blender -b --factory-startup -noaudio --python blender_build.py -- spec.json

Spec format (see templates/specs/ac_cycle.json for a full example):
{
  "name": "ac_cycle",
  "export": "/abs/path/out.glb",
  "materials": {
    "Material_Utama": {"color": [1,1,1,1], "metallic": 0.0, "roughness": 0.6}
  },
  "components": [
    {"name": "Evaporator", "parts": [
      {"prim": "cube", "size": [1.5, 0.32, 0.42], "loc": [-2.0, -1.35, 1.7],
       "rot": [0, 0, 0], "material": "Material_Utama"},
      {"prim": "pipe", "points": [[...], [...]], "radius": 0.03,
       "material": "Material_Tembaga"}
    ]}
  ]
}
Primitives: cube, cylinder, sphere, torus, cone, pipe.
Coordinates: Blender space, X right, Y depth, Z up, metres.
"""
import sys
import json
import math
import os

import bpy


# ---------------------------------------------------------------- helpers
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.cameras, bpy.data.lights):
        pass  # data blocks are pruned on save/export; keep it simple


def get_material(name, spec):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mdef = spec.get("materials", {}).get(name, {})
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    color = mdef.get("color", [0.8, 0.8, 0.8, 1.0])
    bsdf.inputs["Base Color"].default_value = tuple(color)
    bsdf.inputs["Metallic"].default_value = mdef.get("metallic", 0.0)
    bsdf.inputs["Roughness"].default_value = mdef.get("roughness", 0.6)
    if "emissive" in mdef:
        bsdf.inputs["Emission Color"].default_value = tuple(mdef["emissive"])
        bsdf.inputs["Emission Strength"].default_value = mdef.get(
            "emission_strength", 1.0)
    return mat


def set_transform(obj, loc, rot_deg):
    obj.location = tuple(loc)
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)


def auto_uv(obj):
    """Smart UV-project every mesh so textures/shaders have sane UVs."""
    try:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as exc:  # noqa: BLE001 - never fail a build on UVs
        print(f"[blender_build] UV warning on {obj.name}: {exc}")
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass


def finish_part(obj, part, spec, parent):
    obj.name = part.get("name", obj.name)
    mat_name = part.get("material", "Material_Utama")
    obj.data.materials.append(get_material(mat_name, spec))
    set_transform(obj, part.get("loc", [0, 0, 0]), part.get("rot", [0, 0, 0]))
    auto_uv(obj)
    obj.parent = parent
    return obj


def add_cube(part, spec, parent):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.dimensions = tuple(part.get("size", [1, 1, 1]))
    # dimensions are applied on top of unit cube; reset scale via transform
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish_part(obj, part, spec, parent)


def add_cylinder(part, spec, parent):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=part.get("radius", 0.5),
        depth=part.get("depth", 1.0),
        vertices=part.get("vertices", 48))
    return finish_part(bpy.context.active_object, part, spec, parent)


def add_sphere(part, spec, parent):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=part.get("radius", 0.5),
        segments=part.get("segments", 32),
        ring_count=part.get("rings", 16))
    return finish_part(bpy.context.active_object, part, spec, parent)


def add_torus(part, spec, parent):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=part.get("major_radius", 0.5),
        minor_radius=part.get("minor_radius", 0.1),
        major_segments=part.get("major_segments", 48),
        minor_segments=part.get("minor_segments", 12))
    return finish_part(bpy.context.active_object, part, spec, parent)


def add_cone(part, spec, parent):
    bpy.ops.mesh.primitive_cone_add(
        radius1=part.get("radius1", 0.5),
        radius2=part.get("radius2", 0.0),
        depth=part.get("depth", 1.0),
        vertices=part.get("vertices", 48))
    return finish_part(bpy.context.active_object, part, spec, parent)


def add_pipe(part, spec, parent):
    """Thin tube through waypoints: cylinders + joint spheres (one mesh group)."""
    pts = [tuple(p) for p in part["points"]]
    radius = part.get("radius", 0.03)
    group = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-6:
            continue
        mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2]
        # cylinder default axis is Z; rotate Z-axis onto (dx,dy,dz)
        z_axis = (0.0, 0.0, 1.0)
        direction = (dx / length, dy / length, dz / length)
        # quaternion from Z to direction
        cross = (z_axis[1] * direction[2] - z_axis[2] * direction[1],
                 z_axis[2] * direction[0] - z_axis[0] * direction[2],
                 z_axis[0] * direction[1] - z_axis[1] * direction[0])
        dot = z_axis[0] * direction[0] + z_axis[1] * direction[1] + \
            z_axis[2] * direction[2]
        if dot < -0.9999:
            quat = (0.0, 1.0, 0.0, 0.0)
        else:
            w = math.sqrt(1.0 + dot)
            quat = (w / math.sqrt(2.0),
                    cross[0] / (math.sqrt(2.0) * w),
                    cross[1] / (math.sqrt(2.0) * w),
                    cross[2] / (math.sqrt(2.0) * w))
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length,
                                            vertices=24)
        obj = bpy.context.active_object
        obj.location = tuple(mid)
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = quat
        obj.data.materials.append(
            get_material(part.get("material", "Material_Tembaga"), spec))
        auto_uv(obj)
        obj.parent = parent
        group.append(obj)
    for p in pts:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius * 1.05,
                                             segments=16, ring_count=8)
        obj = bpy.context.active_object
        obj.location = tuple(p)
        obj.data.materials.append(
            get_material(part.get("material", "Material_Tembaga"), spec))
        obj.parent = parent
        group.append(obj)
    return group


PRIMS = {
    "cube": add_cube,
    "cylinder": add_cylinder,
    "sphere": add_sphere,
    "torus": add_torus,
    "cone": add_cone,
    "pipe": add_pipe,
}


def build(spec):
    clean_scene()
    for comp in spec["components"]:
        empty = bpy.data.objects.new(comp["name"], None)
        bpy.context.collection.objects.link(empty)
        for part in comp["parts"]:
            prim = part["prim"]
            if prim not in PRIMS:
                raise ValueError(f"unknown primitive: {prim}")
            PRIMS[prim](part, spec, empty)
    # select all for export
    bpy.ops.object.select_all(action='SELECT')
    out = spec["export"]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=out, export_format='GLB', export_apply=True,
        export_yup=True, export_materials='EXPORT')
    print(f"[blender_build] EXPORTED {out} "
          f"({os.path.getsize(out)} bytes, "
          f"{len(spec['components'])} components)")


def main():
    argv = sys.argv
    spec_path = argv[argv.index("--") + 1] if "--" in argv else None
    if not spec_path:
        raise SystemExit("usage: blender -b --python blender_build.py -- spec.json")
    with open(spec_path, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    build(spec)


if __name__ == "__main__":
    main()
