import bpy, sys, math, mathutils
argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
COMP = argv[2] if len(argv) > 2 else "AcOutdoor"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=src)
meshes = [ob for ob in bpy.context.scene.objects if ob.type == 'MESH']
assert len(meshes) >= 1, "no mesh imported"
# TripoSR OBJ is Z-up (long axis = Z, fans stacked along Z).
# Blender is Z-up too, but the importer assumes Y-up and adds a -90deg X
# object rotation. We bake the CORRECT orientation directly into the
# vertex data (no operators -- transform_apply is unreliable headless):
# R_x(-90deg) maps +Z -> +Y... in Blender coords we want long axis on +Z.
# OBJ coords already have long axis on Z == Blender Z, so the only fix is
# to DROP the importer's object rotation; the mesh data stays as-is.
# (Previous attempt baked R_x(+90deg) via transform_apply -- it silently
#  did nothing headless, and +90deg was the wrong direction anyway.)
for ob in meshes:
    ob.rotation_euler = (0, 0, 0)
    ob.location = (0, 0, 0)
    # vertex-color lift: TripoSR colors come out dark/shaded
    me = ob.data
    for attr in me.color_attributes:
        for d in attr.data:
            r, g, b, a = d.color
            d.color = (min(1.0, r * 1.6), min(1.0, g * 1.6), min(1.0, b * 1.6), a)
    # center on origin (XY), base at z=0 -- in OBJ coords Z is up
    bb = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
    cx = sum(v.x for v in bb) / 8; cy = sum(v.y for v in bb) / 8
    minz = min(v.z for v in bb)
    ob.location.x -= cx; ob.location.y -= cy; ob.location.z -= minz
    print("MESH", ob.name, "bbox Z range:", round(min(v.z for v in bb),2), "..", round(max(v.z for v in bb),2))
# wrap in an empty GROUP named AcOutdoor (viewer pivot logic needs a group
# with mesh children; a bare mesh gets removed when pivoted)
grp = bpy.data.objects.new(COMP, None)
bpy.context.scene.collection.objects.link(grp)
for i, ob in enumerate(meshes):
    ob.name = f"{COMP}Mesh{i}" if len(meshes) > 1 else f"{COMP}Mesh"
    ob.parent = grp
    ob.matrix_parent_inverse = grp.matrix_world.inverted()
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB')
print("GLB_EXPORTED", dst, "meshes:", len(meshes))
