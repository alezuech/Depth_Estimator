import bpy
import bmesh
from mathutils import Vector
import numpy as np
import math
import mathutils
from bpy import context

# run this script from the command line with this command
# blender --background main.blend --python main.py


# this is needed to import functions from another python file
import sys
import os
dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir )
import functions
# this next part forces a reload in case you edit the source after you first start the blender session
import imp
imp.reload(functions)
# this is optional and allows you to call the functions without specifying the package name
from functions import *


cam_loc = bpy.data.objects['Camera'].location

# add an Empty at world origin, set the camera to track it, apply the constraint and remove the Empty
bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
for obj in bpy.context.selected_objects:
    obj.name = "myEmpty"
    
constraint = bpy.data.objects['Camera'].constraints.new(type='TRACK_TO')
constraint.target = bpy.data.objects['myEmpty']
camera = bpy.data.objects["Camera"]
camera.select_set(True)    
bpy.context.view_layer.objects.active = camera
bpy.ops.constraint.apply(constraint='Track To', owner='OBJECT', report=False)
object_to_delete = bpy.data.objects['myEmpty']
bpy.data.objects.remove(object_to_delete, do_unlink=True)

# get the FOVs, create a plane parallel to the camera and place it in front of it, then resize it to match the FOV
h, v = get_FOVs()
camera_rotation = camera.rotation_euler
background_loc = -camera.location * 1
camera_background_dist = VectorLength(background_loc) + VectorLength(camera.location)
b = abs(2 * math.tan(math.radians(h)/2)*camera_background_dist)
bpy.ops.mesh.primitive_plane_add(size = b, enter_editmode=False, align='WORLD', location=background_loc, scale=(1,1,1), rotation=camera_rotation)
for obj in bpy.context.selected_objects:
    obj.name = "BackgroundPlane"


# vertices = object_vertices(context.active_object)
vertices = object_vertices(bpy.data.objects["Plane.001"])
for v in vertices:
    print(v)

obj1 = bpy.data.objects["BackgroundPlane"]
obj2 = bpy.data.objects["Cube.001"]

check = bmesh_check_intersect_objects(obj1, obj2)

print(f'\nIntersection: {check}')



x_res = bpy.data.scenes['Scene'].render.resolution_x
y_res = bpy.data.scenes['Scene'].render.resolution_y

subdivision_levels = int(math.log2(x_res))
print('levels: ', subdivision_levels)


# pick any object
obj = bpy.data.objects['BackgroundPlane']
# set the object to active
bpy.context.view_layer.objects.active = obj
# this operator will 'work' or 'operate' on the active object we just set
# bpy.ops.object.modifier_apply(modifier="my_modifier_name")


# bpy.context.view_layer.objects.active = bpy.data.objects["BackgroundPlane"]
bpy.ops.object.modifier_add(type='MULTIRES')
for i in range(subdivision_levels):
    bpy.ops.object.multires_subdivide(modifier="Multires", mode='SIMPLE')
bpy.ops.object.modifier_apply(modifier="Multires")








bpy.ops.object.mode_set(mode='EDIT')

ob = bpy.context.active_object
me = ob.data
bm = bmesh.from_edit_mesh(me)

for f in bm.faces:
    print(f)
    for e in f.edges:
        for v in e.verts:
            print(f'face {f.index} - edge {e.index} - vert {v.co}')
    # if f.select:
    #     print(f.index)
    #     for v in bm.verts:
    #         print(v.co)


# apply a subdivision modifier to the plane to match the pixels of the final image
# create the single "pyramids"
# for each pyramid, check what are the intersected objects
# apply a simple subdivision modifier to the intersected mesh
# obtain the intersection between a pyramid and a copy of the scene
# apply a remesh modifier to the intersected mesh
# 