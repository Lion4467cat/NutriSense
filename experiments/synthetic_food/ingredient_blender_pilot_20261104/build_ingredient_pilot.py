"""Seeded Blender bpy pilot for three ingredient-level WED food classes.

All visible food geometry is authored in this script. Geometry Nodes instance
the reusable ingredient meshes; rendered masks and metric depth come from the
same scene graph. Density remains an explicit, uncertain project prior.
"""
from __future__ import annotations

import json
import math
import random
import sys
import argparse
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "datasets/processed/synthetic_food_ingredient_blender_pilot_20261104"
INPUTS = OUT / "inputs.json"
MARKER_TEXTURE = OUT / "marker_id7_60mm_on_85mm_card.png"
BLEND_DIR = Path(__file__).resolve().parent / "blend_templates"
WIDTH, HEIGHT = 448, 336
CLASS_IDS = {"chicken-dum-biryani": 12, "Bottle-gourd-curry": 1, "salad": 32}
CLASS_LABELS = {12: "chicken-dum-biryani", 1: "Bottle-gourd-curry", 32: "salad"}
CAMERA_KINDS = {"isolated": (0.62, 60.0), "composed": (0.90, 62.0)}  # distance m, elevation degrees


def json_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    for pool in (bpy.data.meshes, bpy.data.materials, bpy.data.node_groups, bpy.data.cameras,
                 bpy.data.lights, bpy.data.curves):
        for datablock in list(pool):
            if datablock.users == 0:
                pool.remove(datablock)


def srgb_to_linear(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return c / 12.92 if c < 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def mat_rgb(rgb, name: str, *, roughness: float = 0.62, noise_scale: float = 100.0,
            bump_strength: float = 0.11, bump_distance: float = 0.00022, metallic: float = 0.0):
    base = tuple(srgb_to_linear(float(x) / 255.0) for x in rgb)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*base, 1.0)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.72
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (*[v * 0.73 for v in base], 1.0)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (*[min(1, v * 1.25 + 0.035) for v in base], 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = bump_distance
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def simple_mat(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def mesh_obj(name, verts, faces, material, *, pass_index=0, material_indices=None):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    if material_indices:
        for poly, idx in zip(mesh.polygons, material_indices):
            poly.material_index = idx
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.pass_index = pass_index
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def rice_grain(name, material, seed, scale=1.0):
    """Closed, tapered ellipsoid kernel; dimensions are metres."""
    rng = random.Random(seed)
    length, width, height = 0.0092 * scale, 0.0035 * scale, 0.00245 * scale
    # A slightly curved longitudinal axis and tapered end rings.
    profile = [(0.02, 0.12), (0.12, 0.52), (0.32, 0.84), (0.5, 1.0),
               (0.68, 0.84), (0.88, 0.52), (0.98, 0.12)]
    sides = 8
    verts = []
    for t, rad in profile:
        x = (t - 0.5) * length
        curve = math.sin(t * math.pi) * rng.uniform(-0.00012, 0.00012)
        for j in range(sides):
            a = 2 * math.pi * j / sides
            verts.append((x, math.cos(a) * width * 0.5 * rad + curve,
                          math.sin(a) * height * 0.5 * rad))
    faces = [tuple(range(sides - 1, -1, -1))]
    for i in range(len(profile) - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    start = (len(profile) - 1) * sides
    faces.append(tuple(start + j for j in range(sides)))
    return mesh_obj(name, verts, faces, material)


def rounded_chunk(name, dims, material, seed, *, pass_index=0):
    """Procedural bevelled and mildly irregular food cube, closed manifold."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.pass_index = pass_index
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Soft cut edges", "BEVEL")
    bevel.width = min(dims) * 0.17
    bevel.segments = 2
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    rng = random.Random(seed)
    for vert in obj.data.vertices:
        for axis in range(3):
            vert.co[axis] += rng.uniform(-1, 1) * dims[axis] * 0.035
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def irregular_food_piece(name, dims, material, seed, *, pass_index=0, subdivisions=1):
    """Closed, non-cuboid cooked ingredient piece with seeded irregular facets."""
    rng=random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions,radius=1,location=(0,0,0))
    obj=bpy.context.object;obj.name=name;obj.pass_index=pass_index
    for vert in obj.data.vertices:
        v=vert.co.normalized()
        noise=rng.uniform(.88,1.12)
        vert.co.x*=dims[0]*.5*noise
        vert.co.y*=dims[1]*.5*noise
        vert.co.z*=dims[2]*.5*noise
    obj.data.materials.append(material)
    for poly in obj.data.polygons:poly.use_smooth=True
    return obj


def cucumber_slice(name, radius, thickness, rind, flesh, seed, *, pass_index=32):
    """Closed cucumber disk with a dark peel band and seed-like top regions."""
    rng = random.Random(seed)
    n, rings = 48, 3
    verts = []
    # bottom centre, top centre, then bottom/top perimeter rings
    verts.extend([(0, 0, -thickness / 2), (0, 0, thickness / 2)])
    for z in (-thickness / 2, thickness / 2):
        for j in range(n):
            ang = 2 * math.pi * j / n
            local_r = radius * (1 + 0.025 * math.sin(5 * ang + seed))
            verts.append((local_r * math.cos(ang), local_r * math.sin(ang), z))
    faces, mids = [], []
    bottom0, top0 = 2, 2 + n
    for j in range(n):
        k = (j + 1) % n
        faces.append((0, bottom0 + k, bottom0 + j)); mids.append(1)
        faces.append((bottom0 + j, bottom0 + k, top0 + k, top0 + j)); mids.append(0)
    faces.append(tuple(top0+j for j in range(n)));mids.append(1)
    obj = mesh_obj(name, verts, faces, rind, pass_index=pass_index, material_indices=mids)
    obj.data.materials.append(flesh)
    obj.data.materials.append(simple_mat(name + " seed speckles", (0.48, 0.49, 0.34), roughness=0.7))
    return obj


def cucumber_seed_oval(name, material, seed, *, pass_index=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=(0,0,0))
    obj=bpy.context.object;obj.name=name;obj.pass_index=pass_index
    obj.scale=(.0024,.00085,.00032)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    rng=random.Random(seed)
    for v in obj.data.vertices:
        v.co.x*=rng.uniform(.8,1.2);v.co.y*=rng.uniform(.85,1.15)
    obj.data.materials.append(material)
    for poly in obj.data.polygons:poly.use_smooth=True
    return obj


def tomato_slice(name, radius, thickness, skin, flesh, seed):
    n = 40
    verts = [(0, 0, -thickness/2), (0, 0, thickness/2)]
    for z in (-thickness/2, thickness/2):
        for j in range(n):
            a = 2*math.pi*j/n
            r = radius*(1+0.035*math.sin(4*a+seed))
            verts.append((r*math.cos(a),r*math.sin(a),z))
    faces=[]; mids=[]; b0=2; t0=2+n
    for j in range(n):
        k=(j+1)%n
        faces.append((b0+j,b0+k,t0+k,t0+j));mids.append(0)
    faces.append(tuple(b0+j for j in reversed(range(n))));mids.append(1)
    faces.append(tuple(t0+j for j in range(n)));mids.append(1)
    obj=mesh_obj(name,verts,faces,skin,material_indices=mids)
    obj.data.materials.append(flesh)
    return obj


def sauce_mesh(name, radius, height, material, seed, pass_index):
    """Watertight shallow, irregular gravy pool; analytic surface noise is seeded."""
    rng = random.Random(seed)
    segments, rings = 64, 10
    verts = [(0, 0, 0.003), (0, 0, height)]
    # bottom rim followed by top rings
    for j in range(segments):
        a = 2*math.pi*j/segments
        r = radius*(1+0.035*math.sin(3*a+seed*0.2)+0.02*math.sin(7*a))
        verts.append((r*math.cos(a), r*math.sin(a), 0.003))
    bottom_ring = 2
    top_offsets=[]
    for ri in range(1, rings+1):
        frac=ri/rings
        top_offsets.append(len(verts))
        for j in range(segments):
            a=2*math.pi*j/segments
            r=radius*frac*(1+0.025*math.sin(4*a+seed))
            ripple=(0.0006*math.sin(8*a+seed)+0.00035*math.sin(0.0003*j+seed))*frac
            z=height+ripple-0.0012*frac
            verts.append((r*math.cos(a),r*math.sin(a),z))
    faces=[]
    for j in range(segments):
        k=(j+1)%segments
        faces.append((0,bottom_ring+j,bottom_ring+k))
        # outer wall joins bottom rim to final top ring
        top_last=top_offsets[-1]
        faces.append((bottom_ring+j,top_last+j,top_last+k,bottom_ring+k))
        # top fan/rings
    first=top_offsets[0]
    for j in range(segments): faces.append((1,first+j,first+(j+1)%segments))
    for ri in range(len(top_offsets)-1):
        a0,b0=top_offsets[ri],top_offsets[ri+1]
        for j in range(segments):
            k=(j+1)%segments
            faces.append((a0+j,b0+j,b0+k,a0+k))
    return mesh_obj(name,verts,faces,material,pass_index=pass_index)


def leaf_mesh(name, material, seed):
    # Small closed, pointed leaf with a shallow raised central vein.
    length=0.025; width=0.008; thick=0.0007
    verts=[]
    stations=[(-0.5,0.04),(-0.28,0.65),(0,1),(0.28,0.65),(0.5,0.04)]
    for x,w in stations:
        for y,z in [(-width*w/2,0),(0,thick),(width*w/2,0),(0,-thick/2)]:
            verts.append((x*length,y, z + (0.00012*math.sin(seed+x*10) if z>=0 else 0)))
    faces=[]
    for i in range(len(stations)-1):
        a=i*4;b=(i+1)*4
        for j in range(4): faces.append((a+j,a+(j+1)%4,b+(j+1)%4,b+j))
    faces.extend([(0,3,2,1),(16,17,18,19)])
    return mesh_obj(name,verts,faces,material)


def torus_onion(name, major_r, minor_r, material, *, pass_index=32):
    bpy.ops.mesh.primitive_torus_add(major_segments=32, minor_segments=8,
                                     major_radius=major_r, minor_radius=minor_r,
                                     location=(0,0,0))
    obj=bpy.context.object; obj.name=name; obj.pass_index=pass_index
    obj.data.materials.append(material)
    for poly in obj.data.polygons: poly.use_smooth=True
    return obj


def make_gn_scatter(host_name, source, points, object_id, seed, yaw_span, scale_range=(1.0,1.0)):
    mesh=bpy.data.meshes.new(host_name+"PointsMesh")
    mesh.from_pydata(points, [], [])
    mesh.update()
    host=bpy.data.objects.new(host_name,mesh)
    bpy.context.scene.collection.objects.link(host)
    host.pass_index=object_id
    tree=bpy.data.node_groups.new(host_name+"_GeometryNodes","GeometryNodeTree")
    tree.interface.new_socket(name="Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
    nodes=tree.nodes; links=tree.links
    inp=nodes.new("NodeGroupInput"); out=nodes.new("NodeGroupOutput")
    to_points=nodes.new("GeometryNodeMeshToPoints"); to_points.mode="VERTICES"
    obj_info=nodes.new("GeometryNodeObjectInfo")
    obj_info.inputs["Object"].default_value=source
    if "As Instance" in obj_info.inputs: obj_info.inputs["As Instance"].default_value=True
    if hasattr(obj_info,"transform_space"): obj_info.transform_space="ORIGINAL"
    inst=nodes.new("GeometryNodeInstanceOnPoints")
    idx=nodes.new("GeometryNodeInputIndex")
    rand=nodes.new("FunctionNodeRandomValue"); rand.data_type="FLOAT_VECTOR"
    rand.inputs["Min"].default_value=(-0.18,-0.18,-yaw_span)
    rand.inputs["Max"].default_value=(0.18,0.18,yaw_span)
    rand.inputs["Seed"].default_value=int(seed)
    if "ID" in rand.inputs: links.new(idx.outputs["Index"],rand.inputs["ID"])
    scale_rand=nodes.new("FunctionNodeRandomValue");scale_rand.data_type="FLOAT_VECTOR"
    scale_rand.inputs["Min"].default_value=(scale_range[0],scale_range[0],scale_range[0])
    scale_rand.inputs["Max"].default_value=(scale_range[1],scale_range[1],scale_range[1])
    scale_rand.inputs["Seed"].default_value=int(seed+1009)
    if "ID" in scale_rand.inputs: links.new(idx.outputs["Index"],scale_rand.inputs["ID"])
    realize=nodes.new("GeometryNodeRealizeInstances")
    links.new(inp.outputs["Geometry"],to_points.inputs["Mesh"])
    links.new(to_points.outputs["Points"],inst.inputs["Points"])
    links.new(obj_info.outputs["Geometry"],inst.inputs["Instance"])
    links.new(rand.outputs["Value"],inst.inputs["Rotation"])
    links.new(scale_rand.outputs["Value"],inst.inputs["Scale"])
    links.new(inst.outputs["Instances"],realize.inputs["Geometry"])
    links.new(realize.outputs["Geometry"],out.inputs["Geometry"])
    mod=host.modifiers.new("Seeded ingredient scatter","NODES")
    mod.node_group=tree
    source.hide_render=True
    source.hide_set(True)
    return host


def make_root(name, offset):
    root=bpy.data.objects.new(name,None)
    bpy.context.scene.collection.objects.link(root)
    root.location=(offset[0],offset[1],0)
    return root


def parent_to_root(obj, root):
    obj.parent=root


def evaluated_volume_m3(obj):
    deps=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(deps)
    mesh=ev.to_mesh()
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bm.transform(ev.matrix_world)
    try:
        volume=abs(float(bm.calc_volume(signed=True)))
    except Exception:
        volume=0.0
    bm.free(); ev.to_mesh_clear()
    return volume


def look_at(obj, point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()


def setup_scene(seed, kind, camera_distance, elevation_deg, *, lights_scale=1.0):
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.cycles.seed=int(seed)
    scene.cycles.use_animated_seed=False
    scene.cycles.use_adaptive_sampling=False
    scene.render.resolution_x=WIDTH;scene.render.resolution_y=HEIGHT;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    scene.render.film_transparent=False
    scene.view_settings.view_transform="AgX"
    scene.unit_settings.system="METRIC";scene.unit_settings.scale_length=1.0
    scene.frame_set(1)
    scene.world.color=(0.10,0.10,0.10)
    if scene.world.use_nodes:
        bg=scene.world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs["Color"].default_value=(0.34,0.33,0.30,1)
            bg.inputs["Strength"].default_value=.14
    scene.view_settings.look="AgX - Medium High Contrast"
    # A restrained exposure keeps pale flesh and plate whites from washing out
    # the ingredient-specific color cues at this small review resolution.
    scene.view_settings.exposure=-.85
    ground_mat=mat_rgb((166,157,137),"Warm matte stone table",roughness=.84,noise_scale=38,bump_strength=.08,bump_distance=.0003)
    bpy.ops.mesh.primitive_plane_add(size=3,location=(0,0,-0.007))
    ground=bpy.context.object;ground.name="Ground";ground.data.materials.append(ground_mat)
    ground.pass_index=0

    # Soft but directional natural-window key, broad fill and a subtle rim.
    bpy.ops.object.light_add(type="AREA",location=(-.38,-.28,.62))
    key=bpy.context.object;key.name="Window key";key.data.energy=58*lights_scale;key.data.shape="RECTANGLE";key.data.size=.50;key.data.size_y=.35;look_at(key,(0,0,0))
    bpy.ops.object.light_add(type="AREA",location=(.38,.18,.42))
    fill=bpy.context.object;fill.name="Soft fill";fill.data.energy=12*lights_scale;fill.data.shape="DISK";fill.data.size=.38;look_at(fill,(0,0,.02))
    bpy.ops.object.light_add(type="AREA",location=(0,.5,.48))
    rim=bpy.context.object;rim.name="Window bounce";rim.data.energy=8*lights_scale;rim.data.size=.4;look_at(rim,(0,0,.02))

    distance=camera_distance
    elev=math.radians(elevation_deg)
    bpy.ops.object.camera_add(location=(0,-distance*math.cos(elev),distance*math.sin(elev)))
    cam=bpy.context.object;cam.name="Metric camera";cam.data.type="PERSP";cam.data.lens=50;cam.data.sensor_width=36;cam.data.sensor_fit="HORIZONTAL";cam.data.clip_start=.01;cam.data.clip_end=4
    look_at(cam,(0,0,.012));scene.camera=cam
    scene.render.filepath="//render.png"

    return scene,cam


def add_plate(name, center, radius, *, material=None, thickness=.006):
    if material is None:
        material=simple_mat("Warm white ceramic",(.82,.81,.75),roughness=.24)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=radius,depth=thickness,location=(center[0],center[1],-thickness/2))
    obj=bpy.context.object;obj.name=name;obj.data.materials.append(material);obj.pass_index=0
    bevel=obj.modifiers.new("Rounded ceramic lip","BEVEL");bevel.width=.004;bevel.segments=3
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=bevel.name)
    for p in obj.data.polygons:p.use_smooth=True
    bpy.ops.mesh.primitive_torus_add(major_radius=radius*.91,minor_radius=.003,major_segments=96,minor_segments=12,location=(center[0],center[1],.001))
    rim=bpy.context.object;rim.name=name+" raised rim";rim.data.materials.append(material);rim.pass_index=0
    return obj


def add_bowl(name, center, radius=.073, height=.025):
    """Closed shallow metal bowl; geometry is vessel context, not food label."""
    steel=simple_mat(name+" brushed stainless steel",(.34,.37,.39),roughness=.25,metallic=.72)
    profile=[(.001,.001),(.36*radius,.001),(.63*radius,.002),(.81*radius,.007),
             (.94*radius,.014),(radius,height),(radius*.985,height+.001)]
    seg=96;verts=[]
    for r,z in profile:
        for j in range(seg):
            a=math.tau*j/seg
            verts.append((center[0]+r*math.cos(a),center[1]+r*math.sin(a),z))
    faces=[]
    faces.append(tuple(reversed(range(seg))))
    for ring in range(len(profile)-1):
        a0=ring*seg;b0=(ring+1)*seg
        for j in range(seg):
            k=(j+1)%seg;faces.append((a0+j,a0+k,b0+k,b0+j))
    faces.append(tuple((len(profile)-1)*seg+j for j in range(seg)))
    bowl=mesh_obj(name,verts,faces,steel,pass_index=0)
    bpy.ops.mesh.primitive_torus_add(major_segments=96,minor_segments=12,
        major_radius=radius*.994,minor_radius=.0014,
        location=(center[0],center[1],height))
    rim=bpy.context.object;rim.name=name+" rolled rim";rim.data.materials.append(steel);rim.pass_index=0
    return bowl


def add_card(seed, card_center):
    spec=json.loads(INPUTS.read_text(encoding="utf-8"))["aruco_marker"]
    white=simple_mat("Marker paper white",(.94,.94,.92),roughness=.9)
    black=simple_mat("Marker ink black",(.004,.004,.004),roughness=.9)
    side=.085;half=side/2;marker_half=.03;z=.001
    verts=[(-half,-half,0),(half,-half,0),(half,half,0),(-half,half,0)]
    faces=[(0,1,2,3)];material_ids=[0]
    for row,modules in enumerate(spec["black_modules"]):
        y_hi=marker_half-row*spec["module_side_mm"]/1000
        y_lo=y_hi-spec["module_side_mm"]/1000
        for col,is_black in enumerate(modules):
            if not is_black:continue
            x_lo=-marker_half+col*spec["module_side_mm"]/1000
            x_hi=x_lo+spec["module_side_mm"]/1000
            base=len(verts)
            verts.extend([(x_lo,y_lo,.0001),(x_hi,y_lo,.0001),
                          (x_hi,y_hi,.0001),(x_lo,y_hi,.0001)])
            faces.append((base,base+1,base+2,base+3));material_ids.append(1)
    obj=mesh_obj("Card ID7 60mm",verts,faces,white,pass_index=0,material_indices=material_ids)
    obj.location=(card_center[0],card_center[1],z);obj.data.materials.append(black)
    for attr in ("visible_diffuse","visible_glossy","visible_transmission","visible_volume_scatter","visible_shadow"):
        if hasattr(obj,attr):setattr(obj,attr,False)
    return obj


def marker_projection(scene, camera, card_obj):
    # Card side is 85 mm; the marker is centered and 60 mm square.
    from bpy_extras.object_utils import world_to_camera_view
    # Camera transforms can be dirty after the seeded orbit/look-at update.
    # Flush the dependency graph before projecting corners into image space.
    bpy.context.view_layer.update()
    cx,cy,cz=card_obj.location
    corners=[(cx-.03,cy-.03,cz),(cx+.03,cy-.03,cz),(cx+.03,cy+.03,cz),(cx-.03,cy+.03,cz)]
    projected=[]
    for c in corners:
        p=world_to_camera_view(scene,camera,Vector(c))
        projected.append([float(p.x*WIDTH),float((1-p.y)*HEIGHT)])
    return {"dictionary":"DICT_4X4_50","marker_id":7,"marker_side_mm":60.0,
            "card_side_mm":85.0,"world_corners_m":corners,"image_corners_px":projected,
            "card_center_m":list(card_obj.location),
            "card_corners_world_m":[[cx-.0425,cy-.0425,cz],[cx+.0425,cy-.0425,cz],
                                     [cx+.0425,cy+.0425,cz],[cx-.0425,cy+.0425,cz]]}


def make_rice_stack_points(seed, count):
    rng=random.Random(seed)
    pts=[]
    layer_count=8
    per_layer=math.ceil(count/layer_count)
    for layer in range(layer_count):
        # Random disk-like layers remove the conspicuous rows of a simple lattice.
        shrink=1.0-0.026*layer
        rx=.092*shrink;ry=.078*shrink
        z=.0045+layer*.0028
        layer_pts=[]
        for _ in range(per_layer):
            theta=rng.random()*math.tau
            radius=math.sqrt(rng.random())
            wobble=1+.11*math.sin(3*theta+seed*.07)+.055*math.sin(7*theta+seed*.11)
            xx=rx*radius*wobble*math.cos(theta)
            yy=ry*radius*wobble*math.sin(theta)
            layer_pts.append((xx,yy,z+rng.uniform(-.0011,.0011)))
        pts.extend(layer_pts[:max(0,count-len(pts))])
    if len(pts)<count:raise RuntimeError(f"Rice stack has {len(pts)} points, expected {count}")
    return pts


def grid_points(seed, positions, z_values=None, jitter=.001):
    rng=random.Random(seed);out=[]
    for i,(x,y) in enumerate(positions):
        z=(z_values[i] if z_values else 0.0)
        out.append((x+rng.uniform(-jitter,jitter),y+rng.uniform(-jitter,jitter),z))
    return out


def build_recipe(name, seed, profile, portion_g, density, density_uncertainty, offset=(0,0),
                 *, appearance_group_count=0, object_id_start=1):
    rng=random.Random(seed)
    class_id=CLASS_IDS[name]
    root=make_root(name+" serving",offset)
    food_objs=[];ingredient_counts={};ingredient_object_ids={};next_object_id=object_id_start
    def allocate_id(key):
        nonlocal next_object_id
        oid=next_object_id;next_object_id+=1
        ingredient_object_ids[str(oid)]={"ingredient":key,"class_id":class_id}
        return oid
    def scatter(hostname,source,points,key,s,yaw,scale=(1.0,1.0)):
        return make_gn_scatter(hostname,source,points,allocate_id(key),s,yaw,scale)
    # WED class profiles guide plate-level color range, while ingredient recipes are explicit hypotheses.
    median=profile["appearance_profile_rgb_median"]
    q10=profile["appearance_profile_rgb_q10"];q90=profile["appearance_profile_rgb_q90"]
    def cvar(base, span=.09):
        return tuple(max(0,min(255,int(v+rng.uniform(-1,1)*max(5,(hi-lo)*span)))) for v,lo,hi in zip(base,q10,q90))

    if name=="chicken-dum-biryani":
        # The saved WED TRAIN crop visibly contains long cooked grains and brown pieces.
        # Grain identity is visible; chicken pieces follow the class name and remain an assumption.
        # The visible TRAIN crop has a warm brown cooked-rice distribution;
        # each kernel is varied around that class-level range, not copied from it.
        ivory=mat_rgb(cvar((139,94,48)),"Biryani toasted rice grains",roughness=.58,noise_scale=145,bump_strength=.17,bump_distance=.00015)
        saffron=mat_rgb(cvar((164,105,38)),"Biryani saffron grain",roughness=.56,noise_scale=120,bump_strength=.16,bump_distance=.00016)
        browned=mat_rgb(cvar((91,51,26)),"Biryani browned grain",roughness=.64,noise_scale=115,bump_strength=.17,bump_distance=.00017)
        colors=[(ivory,.57),(saffron,.32),(browned,.11)]
        target_count=int(3900+rng.randint(-250,250))
        all_pts=make_rice_stack_points(seed,target_count)
        rng.shuffle(all_pts)
        start=0
        for i,(material,fraction) in enumerate(colors):
            n=round(target_count*fraction) if i<2 else target_count-start
            pts=all_pts[start:start+n];start+=n
            source=rice_grain(f"Rice grain source {i+1}",material,seed+i,scale=rng.uniform(.94,1.06))
            host=scatter(f"Biryani rice grains color {i+1}",source,pts,f"rice_grains_color_{i+1}",seed+i,0.12,(.94,1.06))
            food_objs.append(host);ingredient_counts[f"rice_grains_{i+1}"]=len(pts)
        chicken=mat_rgb(cvar((89,48,26)),"Chicken dum cooked pieces",roughness=.76,noise_scale=62,bump_strength=.21,bump_distance=.0004)
        chunk=irregular_food_piece("Chicken piece source",(.016,.012,.009),chicken,seed+19,pass_index=class_id)
        positions=[]
        for y in (-.043,-.014,.016,.045):
            for x in (-.056,-.020,.020,.056):
                if rng.random()<.86:positions.append((x+rng.uniform(-.005,.005),y+rng.uniform(-.004,.004)))
        chicken_pts=grid_points(seed+24,positions,[.0275]*len(positions),.001)
        host=scatter("Chicken piece scatter",chunk,chicken_pts,"chicken_pieces",seed+25,.55,(.78,1.22))
        food_objs.append(host);ingredient_counts["chicken_piece_instances"]=len(chicken_pts)

    elif name=="Bottle-gourd-curry":
        gravy=mat_rgb(cvar((49,53,23)),"Bottle gourd curry olive gravy",roughness=.36,noise_scale=75,bump_strength=.18,bump_distance=.00032)
        gourdmat=mat_rgb(cvar((101,113,39)),"Bottle gourd cooked flesh",roughness=.52,noise_scale=90,bump_strength=.15,bump_distance=.00022)
        onionmat=mat_rgb((166,142,92),"Curry onion/translucent garnish",roughness=.48,noise_scale=88,bump_strength=.12,bump_distance=.00015)
        herbmat=mat_rgb((59,83,28),"Curry herb flecks",roughness=.6,noise_scale=120,bump_strength=.13,bump_distance=.00012)
        sauce=sauce_mesh("Olive gravy pool",.050,.013,gravy,seed,allocate_id("curry_gravy"))
        food_objs.append(sauce)
        positions=[]
        for y in (-.034,-.017,0,.017,.034):
            for x in (-.036,-.018,0,.018,.036):
                if x*x/.047**2+y*y/.043**2<.80 and rng.random()<.72:positions.append((x,y))
        rng.shuffle(positions);positions=positions[:25]
        gourd=irregular_food_piece("Bottle gourd chunk source",(.015,.012,.008),gourdmat,seed+8,pass_index=class_id)
        gourd_pts=grid_points(seed+9,positions,[.0171]*len(positions),.002)
        host=scatter("Bottle gourd chunk scatter",gourd,gourd_pts,"bottle_gourd_chunks",seed+10,.75,(.82,1.18))
        food_objs.append(host);ingredient_counts["bottle_gourd_chunks"]=len(gourd_pts)
        # Fine onion rings and herb leaves rest on the sauce surface; total volume is measured from meshes.
        onion=torus_onion("Onion ring source",.006,.00075,onionmat,pass_index=class_id)
        onion_pts=grid_points(seed+11,[(-.028,.009),(.012,-.027),(.030,.016),(-.006,.032)],[.0182]*4,.003)
        host=scatter("Curry onion ring scatter",onion,onion_pts,"onion_rings",seed+12,.8,(.8,1.2))
        food_objs.append(host);ingredient_counts["onion_rings"]=len(onion_pts)
        leaf=leaf_mesh("Herb leaf source",herbmat,seed+13)
        leaf_pts=grid_points(seed+14,[(-.018,-.010),(.005,.008),(.020,-.002),(-.004,.024),(.033,-.020)],[.0186]*5,.003)
        host=scatter("Curry herb leaf scatter",leaf,leaf_pts,"herb_leaves",seed+15,1.2,(.75,1.3))
        food_objs.append(host);ingredient_counts["herb_leaves"]=len(leaf_pts)

    elif name=="salad":
        rind=mat_rgb((52,101,38),"Cucumber peel",roughness=.48,noise_scale=74,bump_strength=.12,bump_distance=.00014)
        flesh=mat_rgb((181,194,127),"Cucumber flesh",roughness=.52,noise_scale=86,bump_strength=.09,bump_distance=.0001)
        tomato_skin=mat_rgb((166,38,24),"Tomato skin",roughness=.42,noise_scale=78,bump_strength=.10,bump_distance=.00012)
        tomato_flesh=mat_rgb((205,56,31),"Tomato flesh",roughness=.48,noise_scale=95,bump_strength=.09,bump_distance=.0001)
        onionmat=mat_rgb((206,187,139),"Onion slices",roughness=.56,noise_scale=100,bump_strength=.08,bump_distance=.0001)
        herbmat=mat_rgb((38,83,31),"Fresh herbs",roughness=.6,noise_scale=100,bump_strength=.15,bump_distance=.00015)
        seedmat=mat_rgb((203,193,148),"Cucumber seed flesh",roughness=.5,noise_scale=95,bump_strength=.05,bump_distance=.00006)
        cucumber=cucumber_slice("Cucumber slice source",.0275,.0055,rind,flesh,seed,pass_index=class_id)
        cukepos=[(-.055,-.034),(0,-.034),(.055,-.034),(-.055,.030),(0,.030),(.055,.030)]
        # Some seeds add a seventh sliced piece; each run has a distinct but countable arrangement.
        if seed%2: cukepos.append((-.027,.086))
        cuke_pts=grid_points(seed+1,cukepos,[.0038]*len(cukepos),.0012)
        host=scatter("Cucumber slice arrangement",cucumber,cuke_pts,"cucumber_slices",seed+2,.20,(.90,1.10))
        food_objs.append(host);ingredient_counts["cucumber_slices"]=len(cuke_pts)
        seed_source=cucumber_seed_oval("Cucumber seed source",seedmat,seed+32,pass_index=class_id)
        seed_points=[]
        for sx,sy in cukepos:
            for ang in (.35,1.61,2.87,4.05,5.25):
                rr=.0072
                seed_points.append((sx+rr*math.cos(ang),sy+rr*math.sin(ang),.0069))
        host=scatter("Cucumber seed details",seed_source,seed_points,"cucumber_seeds",seed+33,.35,(.8,1.2))
        food_objs.append(host);ingredient_counts["cucumber_seed_details"]=len(seed_points)
        tomato=tomato_slice("Tomato slice source",.020,.0048,tomato_skin,tomato_flesh,seed+3)
        tompos=[(-.027,.086),(.027,.086)] if seed%2==0 else [(-.027,-.095),(.027,-.095)]
        t_pts=grid_points(seed+4,tompos,[.0035]*len(tompos),.001)
        host=scatter("Tomato slice arrangement",tomato,t_pts,"tomato_slices",seed+5,.45,(.85,1.15))
        food_objs.append(host);ingredient_counts["tomato_slices"]=len(t_pts)
        onion=torus_onion("Onion ring source",.011,.0012,onionmat,pass_index=class_id)
        onionpos=[(-.035,-.095),(.035,-.095)] if seed%2==0 else [(-.035,.086),(.035,.086)]
        onionpts=grid_points(seed+6,onionpos,[.0042]*len(onionpos),.001)
        host=scatter("Onion ring arrangement",onion,onionpts,"onion_rings",seed+7,.35,(.8,1.2))
        food_objs.append(host);ingredient_counts["onion_rings"]=len(onionpts)
        leaf=leaf_mesh("Salad leaf source",herbmat,seed+8)
        leaves=grid_points(seed+9,[(-.095,0),(.095,0)],[.006]*2,.002)
        host=scatter("Salad herb arrangement",leaf,leaves,"herb_leaves",seed+10,1.1,(.75,1.3))
        food_objs.append(host);ingredient_counts["herb_leaves"]=len(leaves)
    else:
        raise ValueError(name)

    # Parent all recipe geometry around one origin, then scale it to a TRAIN-supported
    # portion volume using the explicit class density prior. This is not visual-mass guessing.
    for obj in food_objs:
        parent_to_root(obj,root)
    bpy.context.view_layer.update()
    base_volumes={obj.name:evaluated_volume_m3(obj) for obj in food_objs}
    base_total=sum(base_volumes.values())
    if base_total<=0: raise RuntimeError(f"Nonpositive source geometry volume for {name}: {base_volumes}")
    target_volume_m3=(portion_g/density)/1_000_000.0
    factor=(target_volume_m3/base_total)**(1/3)
    root.scale=(factor,factor,factor)
    bpy.context.view_layer.update()
    final_volumes={obj.name:evaluated_volume_m3(obj) for obj in food_objs}
    total_volume_m3=sum(final_volumes.values())
    return {
        "name":name,"class_id":class_id,"root":root,"objects":food_objs,
        "base_volume_ml":base_total*1e6,"volume_ml":total_volume_m3*1e6,
        "estimated_mass_g":total_volume_m3*1e6*density,
        "estimated_mass_interval_g":[total_volume_m3*1e6*max(.01,density-density_uncertainty),
                                      total_volume_m3*1e6*(density+density_uncertainty)],
        "density_g_ml":density,"density_uncertainty_g_ml":density_uncertainty,
        "density_status":"assumed_not_measured; volume × uncertain class prior is an estimate, not authoritative ground truth",
        "density_source":profile["density_source"],"density_evidence":profile.get("density_evidence",[]),
        "geometry_scale_factor":factor,
        "ingredient_instance_counts":ingredient_counts,
        "ingredient_object_ids":ingredient_object_ids,
        "next_object_id":next_object_id,
        "appearance_profile_sha256":profile["appearance_profile_sha256"],
        "appearance_profile_train_group_count":appearance_group_count,
        "ingredient_composition_status":profile["ingredient_composition_status"],
        "source_split":"eligible WED TRAIN only",
        "portion_conditioning_g":portion_g,
        "portion_conditioning_status":"observed WED TRAIN quantile; geometry scaled to volume via assumed density",
        "geometry_volume_method":"Blender evaluated Geometry Nodes meshes; world-transformed closed-mesh signed volume via bmesh",
    }


def create_scene_card_position(kind, offset=(0,0)):
    if kind=="isolated":
        # Dish at left, card at right, both fully inside the frame.
        return (.145,-.045)
    # Keep the card clear of the thali while inside the tighter composed frame.
    return (-.25,0.0)


def setup_group_scene(seed, kind, recipes, input_data, *, template_path=None):
    reset_scene()
    params=CAMERA_KINDS[kind]
    scene,camera=setup_scene(seed,kind,*params,lights_scale=.90+(.2*((seed%9)/8)))
    plate_mat=simple_mat("Warm white ceramic",(.84,.82,.76),roughness=.23)
    if kind=="isolated":
        if recipes[0]["name"]=="Bottle-gourd-curry":
            add_bowl("Curry serving bowl",(0,0),radius=.073,height=.025)
        else:
            add_plate("Ceramic plate",(0,0),.112,material=plate_mat)
    else:
        # One tray is the meal surface; curry receives a bowl, not nested side plates.
        add_plate("Thali tray",(0,0),.205,material=plate_mat,thickness=.008)
        for recipe in recipes:
            if recipe["name"]=="Bottle-gourd-curry":
                x,y=recipe["offset"]
                add_bowl("Curry bowl on thali",(x,y),radius=.066,height=.022)

    components=[]
    next_object_id=1
    for recipe in recipes:
        profile=input_data["class_evidence"][recipe["name"]]
        values=profile["portion_quantiles_g"]
        built=build_recipe(recipe["name"],recipe["seed"],profile,float(values[recipe["quantile"]]),
                           float(profile["density_prior_g_ml"]),float(profile["density_uncertainty_g_ml"]),
                           recipe["offset"],appearance_group_count=profile["appearance_profile_train_group_count"],
                           object_id_start=next_object_id)
        components.append(built)
        next_object_id=built["next_object_id"]

    # Marker center determined by framing type; card is the only switched object in pairs.
    card=add_card(seed,create_scene_card_position(kind))
    marker=marker_projection(scene,camera,card)
    # Slight camera orbit and elevation jitter: held fixed within each card pair.
    rng=random.Random(seed)
    if kind=="isolated":
        distance,elevation=CAMERA_KINDS[kind]
    else:
        distance,elevation=CAMERA_KINDS[kind]
    # Nudge target toward scene centroid without altering the measured camera model.
    camera.location.x+=rng.uniform(-.018,.018)
    camera.location.y+=rng.uniform(-.018,.018)
    look_at(camera,(.018 if kind=="isolated" else 0.0,0,.012))
    bpy.context.view_layer.update()
    marker=marker_projection(scene,camera,card)
    camera_meta={
        "type":"perspective","world_units":"metres","position_m":list(camera.location),
        "rotation_euler_rad":list(camera.rotation_euler),"lens_mm":camera.data.lens,
        "sensor_width_mm":camera.data.sensor_width,"sensor_fit":camera.data.sensor_fit,
        "clip_start_m":camera.data.clip_start,"clip_end_m":camera.data.clip_end,
        "resolution_px":[WIDTH,HEIGHT],"pixel_aspect":[1.0,1.0],
        "intrinsic_matrix_px":[[WIDTH*camera.data.lens/camera.data.sensor_width,0,WIDTH*.5],
                                [0,WIDTH*camera.data.lens/camera.data.sensor_width,HEIGHT*.5],[0,0,1]],
        "camera_to_world_matrix_row_major":[[float(v) for v in row] for row in camera.matrix_world],
    }
    if template_path:
        template_path.parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(template_path))

    metadata_base={
        "seed":seed,"scene_kind":kind,"camera":camera_meta,"marker":marker,
        "components":[{k:v for k,v in c.items() if k not in ("root","objects")} for c in components],
        "total_food_mass_estimate_g":sum(c["estimated_mass_g"] for c in components),
        "total_food_volume_ml":sum(c["volume_ml"] for c in components),
        "total_mass_estimate_interval_g":[sum(c["estimated_mass_interval_g"][0] for c in components),
                                          sum(c["estimated_mass_interval_g"][1] for c in components)],
        "object_id_to_class_and_ingredient":{oid:info for c in components for oid,info in c["ingredient_object_ids"].items()},
        "pair_difference":"card visibility only; same scene objects, camera, materials, recipe seed, lighting and render settings",
        "wed_dev_images_used":False,"wed_locked_images_used":False,"aruco_eval_images_used":False,
        "wed_test_images_used":False,"production_model_training":False,
    }
    return scene,camera,card,components,metadata_base


def ray_cast_label_depth(scene,camera,object_id_map):
    """Create camera-Z and class maps by ray casting the exact rendered scene graph."""
    deps=bpy.context.evaluated_depsgraph_get()
    cam_to_world=camera.matrix_world
    world_to_cam=cam_to_world.inverted()
    rotation=cam_to_world.to_3x3()
    fx=WIDTH*camera.data.lens/camera.data.sensor_width
    fy=fx
    cx,cy=WIDTH*0.5,HEIGHT*0.5
    origin=cam_to_world.translation
    depth=np.zeros((HEIGHT,WIDTH),dtype=np.float32)
    class_map=np.zeros((HEIGHT,WIDTH),dtype=np.uint8)
    instance_map=np.zeros((HEIGHT,WIDTH),dtype=np.uint16)
    card_map=np.zeros((HEIGHT,WIDTH),dtype=np.uint8)
    for y in range(HEIGHT):
        py=(cy-(y+0.5))/fy
        for x in range(WIDTH):
            px=((x+0.5)-cx)/fx
            direction=rotation @ Vector((px,py,-1.0))
            direction.normalize()
            hit,location,normal,face,obj,matrix=scene.ray_cast(deps,origin,direction,distance=4.0)
            if not hit: continue
            if getattr(obj,"name","")=="Card ID7 60mm":card_map[y,x]=255
            camera_point=world_to_cam @ location
            camera_z=-float(camera_point.z)
            if camera_z<=0 or not math.isfinite(camera_z):continue
            depth[y,x]=camera_z
            idx=int(getattr(obj,"pass_index",0))
            if str(idx) in object_id_map:
                instance_map[y,x]=idx
                class_map[y,x]=int(object_id_map[str(idx)]["class_id"])
    return depth,class_map,instance_map,card_map


def render_member(scene,camera,card,components,base_meta,pair_id,card_present,sample_id):
    sample_dir=OUT/"scenes"/base_meta["scene_kind"]/pair_id/sample_id
    sample_dir.mkdir(parents=True,exist_ok=True)
    card.hide_render=not card_present
    scene.render.filepath=str(sample_dir/"rgb.png")
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    object_id_map=base_meta["object_id_to_class_and_ingredient"]
    depth,class_map,instance_map,card_map=ray_cast_label_depth(scene,camera,object_id_map)
    food=class_map>0
    metric_depth=depth.copy()
    metric_depth[~np.isfinite(metric_depth)]=0
    metric_depth[metric_depth<0]=0
    # Keep exact camera-Z for all visible surfaces; background is zero/invalid.
    np.save(sample_dir/"metric_depth_m.npy",metric_depth)
    from PIL import Image
    Image.fromarray(class_map,mode="L").save(sample_dir/"food_class_mask.png")
    Image.fromarray((food.astype(np.uint8)*255),mode="L").save(sample_dir/"food_mask.png")
    Image.fromarray(card_map,mode="L").save(sample_dir/"card_mask.png")
    np.save(sample_dir/"ingredient_instance_ids.npy",instance_map)
    meta=dict(base_meta)
    meta["card_present"]=card_present
    meta["card_pair_id"]=pair_id
    meta["sample_id"]=sample_id
    meta["food_mask_pixels"]=int(food.sum())
    meta["food_depth_valid_pixels"]=int(np.count_nonzero((metric_depth>0)&food))
    meta["food_depth_range_m"]=[float(metric_depth[food].min()),float(metric_depth[food].max())] if food.any() else None
    meta["mask_class_ids_present"]=sorted(int(v) for v in np.unique(class_map) if v)
    meta["ingredient_instance_ids_present"]=sorted(int(v) for v in np.unique(instance_map) if v)
    meta["physical_label_status"]="renderer geometry volume × explicit uncertain density prior; not measured mass"
    meta["human_visual_identity"]="PENDING"
    meta["human_realism"]="PENDING"
    meta["human_task_label_approval"]="PENDING"
    if not card_present: meta["marker"]={"status":"absent"}
    json_write(sample_dir/"scene.json",meta)
    row={"pair_id":pair_id,"sample_id":sample_id,"scene_kind":base_meta["scene_kind"],"card_present":card_present,
         "rgb":str((sample_dir/"rgb.png").relative_to(OUT)),"mask":str((sample_dir/"food_class_mask.png").relative_to(OUT)),
         "metric_depth":str((sample_dir/"metric_depth_m.npy").relative_to(OUT)),"metadata":str((sample_dir/"scene.json").relative_to(OUT)),
         "ingredient_instances":str((sample_dir/"ingredient_instance_ids.npy").relative_to(OUT)),
         "card_mask":str((sample_dir/"card_mask.png").relative_to(OUT)),
         "class_ids":meta["mask_class_ids_present"],"food_mask_pixels":meta["food_mask_pixels"],
         "task_validity":{"rgb":"REVIEW_REQUIRED","class_identity":"REVIEW_REQUIRED","mask":"AUTOMATED_CHECK_PENDING","depth":"AUTOMATED_CHECK_PENDING","geometry_volume":"AUTOMATED_CHECK_PENDING","mass_density":"ASSUMPTION_REVIEW_REQUIRED","marker":"AUTOMATED_CHECK_PENDING"}}
    return row


def scene_specs(input_data):
    specs=[];seq=0
    quantiles=["q20","q50","q80"]
    # Three visibly and portion-distinct isolated variants for each WED class.
    for name in ("chicken-dum-biryani","Bottle-gourd-curry","salad"):
        for i,q in enumerate(quantiles):
            seq+=1
            specs.append({"pair_id":f"iso_{name}_{q}","kind":"isolated","seed":20261104+seq*97,
                          "recipes":[{"name":name,"quantile":q,"seed":20261104+seq*97,"offset":(0,0)}],
                          "template":name if q=="q50" else None})
    # Eligible WED TRAIN groups show biryani+salad and curry+salad co-occurrences.
    seq+=1
    specs.append({"pair_id":"meal_biryani_salad","kind":"composed","seed":20261104+seq*97,
                  "recipes":[{"name":"chicken-dum-biryani","quantile":"q50","seed":20261104+seq*97+1,"offset":(-.105,.0)},
                             {"name":"salad","quantile":"q50","seed":20261104+seq*97+2,"offset":(.105,.0)}],
                  "template":"composed_biryani_salad"})
    seq+=1
    specs.append({"pair_id":"meal_curry_salad","kind":"composed","seed":20261104+seq*97,
                  "recipes":[{"name":"Bottle-gourd-curry","quantile":"q50","seed":20261104+seq*97+1,"offset":(-.095,.015)},
                             {"name":"salad","quantile":"q50","seed":20261104+seq*97+2,"offset":(.105,-.015)}],
                  "template":"composed_curry_salad"})
    return specs


def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser=argparse.ArgumentParser()
    parser.add_argument("--limit-scenes",type=int,default=0)
    args=parser.parse_args(argv)
    if not INPUTS.is_file() or not MARKER_TEXTURE.is_file():
        raise FileNotFoundError("Run prepare_inputs.py with the project venv before Blender")
    bpy.context.preferences.filepaths.save_version=0
    input_data=json.loads(INPUTS.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True);BLEND_DIR.mkdir(parents=True,exist_ok=True)
    manifest=[]
    specs=scene_specs(input_data)
    if args.limit_scenes: specs=specs[:args.limit_scenes]
    for spec in specs:
        name=spec["pair_id"]
        scene,camera,card,components,base_meta=setup_group_scene(
            spec["seed"],spec["kind"],spec["recipes"],input_data,
            template_path=(BLEND_DIR/(spec["template"]+".blend") if spec.get("template") else None))
        base_meta["pair_id"]=name
        base_meta["composition_evidence"]=(input_data["observed_train_group_cooccurrences"]
            if spec["kind"]=="composed" else [])
        for card_present in (True,False):
            sample_id=name+("_card" if card_present else "_no_card")
            manifest.append(render_member(scene,camera,card,components,base_meta,
                                          name,card_present,sample_id))
        # Keep memory bounded; the next scene is rebuilt from the seed and inputs.
        reset_scene()
    json_write(OUT/"manifest.json",{
        "schema":"nutrisense_ingredient_blender_pilot_v1","seed":20261104,
        "blender_version":bpy.app.version_string,"render_device":"CPU",
        "scene_pair_count":len(manifest)//2,"image_count":len(manifest),"manifest":manifest,
        "human_review":"PENDING; this script never approves appearance or labels",
        "protected_data_accessed":False,"full_corpus_generation":False,"production_model_training":False,
    })
    print(f"Rendered {len(manifest)} paired images from {len(manifest)//2} seeded scenes to {OUT}")


if __name__=="__main__":
    main()
