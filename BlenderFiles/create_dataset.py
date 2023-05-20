import bpy
import bmesh
from mathutils import Vector
import numpy as np
import math
import mathutils
from bpy import context
# from matplotlib import pyplot as plt

# run this script from the command line with this command
# blender --background main.blend --python create_dataset.py

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

# get the FOVs
h, v = get_FOVs()
camera_rot = camera.rotation_euler
x_res = bpy.data.scenes['Scene'].render.resolution_x
y_res = bpy.data.scenes['Scene'].render.resolution_y

cube = bpy.data.objects["Cube.001"]
depth_img = np.zeros((x_res, y_res))

# compute, in degrees, the horizontal and vertical shifts from the center of the POV
for j in range(y_res):
    for i in range(x_res):
        h_shift = -(h/2 - (i+1)*(h/x_res)+(h/x_res)/2)
        v_shift = -(h/2 - (j+1)*(v/y_res)+(v/y_res)/2)
        sphere_loc = new_cartesian(cam_loc, h_shift*np.pi/180, v_shift*np.pi/180)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, enter_editmode=False, align='WORLD', location=sphere_loc, scale=(1, 1, 1))
        
        my_point = bpy.context.view_layer.objects.active # assign variable
        my_point.select_set(True) # select the object
        cube_bm = bmesh.new()   # create an empty BMesh
        cube_bm.from_mesh(cube.data)  
        d_min = closest_intersection(cam_loc, cube_bm, my_point.location)
        depth_img[i,j] = d_min

obj = bpy.data.objects["Cube"]
# closest_intersection(cam_loc, obj, )
print('cube location: ', obj.location)
np.save('depth.npy', depth_img)
# plt.imshow(depth_img)
# plt.show()


