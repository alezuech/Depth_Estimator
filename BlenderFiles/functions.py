import bpy
import bmesh
from mathutils import Vector
import numpy as np
import math
import mathutils
from bpy import context



# checks the sensor_fit and returns the corresponding FOV for each dimension
def get_FOVs():
    def degrees_FOV(sensor_size, focal_length):
        print(f'focal length: {focal_length}')
        return 2*math.atan(sensor_size/(2*focal_length)) * 180 / math.pi
    camera = bpy.data.cameras['Camera']

    x_res = bpy.data.scenes['Scene'].render.resolution_x
    y_res = bpy.data.scenes['Scene'].render.resolution_y
    res_ratio = x_res / y_res
    h_FOV, v_FOV = 0,0

    if camera.sensor_fit=='VERTICAL':
        v_FOV = degrees_FOV(camera.sensor_height, camera.lens)
        h_FOV = v_FOV * res_ratio
        return h_FOV, v_FOV
    
    h_FOV = degrees_FOV(camera.sensor_width, camera.lens)
    v_FOV = h_FOV / res_ratio
    return h_FOV, v_FOV

def VectorLength(my_Vect):
    return math.sqrt(my_Vect[0]**2 + my_Vect[1]**2 + my_Vect[2]**2)

def bmesh_copy_from_object(obj, transform=True, triangulate=True, apply_modifiers=False):
    """
    Returns a transformed, triangulated copy of the mesh
    """
    assert(obj.type == 'MESH')

    if apply_modifiers and obj.modifiers:
        me = obj.to_mesh(bpy.context.scene, True, 'PREVIEW', calc_tessface=False)
        bm = bmesh.new()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    else:
        me = obj.data
        if obj.mode == 'EDIT':
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()
        else:
            bm = bmesh.new()
            bm.from_mesh(me)

    # Remove custom data layers to save memory
    for elem in (bm.faces, bm.edges, bm.verts, bm.loops):
        for layers_name in dir(elem.layers):
            if not layers_name.startswith("_"):
                layers = getattr(elem.layers, layers_name)
                for layer_name, layer in layers.items():
                    layers.remove(layer)

    if transform:
        bm.transform(obj.matrix_world)

    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces)

    return bm

def bmesh_check_intersect_objects(obj, obj2):
    """
    Check if any faces intersect with the other object

    returns a boolean
    """
    assert(obj != obj2)

    # Triangulate
    bm = bmesh_copy_from_object(obj, transform=True, triangulate=True)
    bm2 = bmesh_copy_from_object(obj2, transform=True, triangulate=True)

    # If bm has more edges, use bm2 instead for looping over its edges
    # (so we cast less rays from the simpler object to the more complex object)
    if len(bm.edges) > len(bm2.edges):
        bm2, bm = bm, bm2

    # Create a real mesh (lame!)
    scene = bpy.context.scene
    me_tmp = bpy.data.meshes.new(name="~temp~")
    bm2.to_mesh(me_tmp)
    bm2.free()
    obj_tmp = bpy.data.objects.new(name=me_tmp.name, object_data=me_tmp)
    # scene.objects.link(obj_tmp)
    bpy.context.collection.objects.link(obj_tmp)
    ray_cast = obj_tmp.ray_cast

    intersect = False

    EPS_NORMAL = 0.000001
    EPS_CENTER = 0.01  # should always be bigger

    #for ed in me_tmp.edges:
    for ed in bm.edges:
        v1, v2 = ed.verts

        # setup the edge with an offset
        co_1 = v1.co.copy()
        co_2 = v2.co.copy()
        co_mid = (co_1 + co_2) * 0.5
        no_mid = (v1.normal + v2.normal).normalized() * EPS_NORMAL
        co_1 = co_1.lerp(co_mid, EPS_CENTER) + no_mid
        co_2 = co_2.lerp(co_mid, EPS_CENTER) + no_mid

        success, co, no, index = ray_cast(co_1, (co_2 - co_1).normalized(), distance = ed.calc_length())
        if index != -1:
            intersect = True
            break

    # scene.objects.unlink(obj_tmp)
    bpy.context.collection.objects.unlink(obj_tmp)
    bpy.data.objects.remove(obj_tmp)
    bpy.data.meshes.remove(me_tmp)

    return intersect

def object_vertices(object):
    v = object.data.vertices
    new_v = [None]*len(v)
    for i in range(len(v)):
        co_final = object.matrix_world @ v[i].co
        # now we can view the location by applying it to an object
        obj_empty = bpy.data.objects.new("Test", None)
        context.collection.objects.link(obj_empty)
        obj_empty.location = co_final
        new_v[i] = co_final

    return new_v
