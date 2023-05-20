import bpy
import bmesh
from mathutils import Vector
import numpy as np
import math
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

def dot_v3v3(v0, v1):
    return (
        (v0[0] * v1[0]) +
        (v0[1] * v1[1]) +
        (v0[2] * v1[2])
    )

def mul_v3_d(v0, d):
    return Vector([
        v0[0] * d,
        v0[1] * d,
        v0[2] * d,]
    )

def line_plane_intersection(p0, n, l0, l):
    '''
    p0: it is a point belonging to the plane.
    n: it is the normal of the plane.
    l0: it is a point belonging to the line.
    l: it is a vector in the direction of the line.
    from https://en.wikipedia.org/wiki/Line%E2%80%93plane_intersection#:~:text=In%20analytic%20geometry%2C%20the%20intersection,the%20plane%20but%20outside%20it.
    '''
    if dot_v3v3(l, n)==0: return np.nan # the line is parallel to the plane. It could be either contained in it or not.
    d = dot_v3v3(p0 - l0, n)/dot_v3v3(l, n)
    return l0 + mul_v3_d(l, d)

def get_face_normal(v1, v2, v3):
    '''
    v1, v2, v3: three Vector variables of positions of vertices of the same face.
    '''
    v12 = v1 - v2
    v13 = v1 - v3
    n = [(v1[1]*v2[2]) - (v1[2]*v2[1]), (v1[2]*v2[0]) - (v1[0]*v2[2]), (v1[0]*v2[1]) - (v1[1]*v2[0])]
    n = Vector(n).normalized()
    return n

def closest_intersection(cam_loc, scene_mesh, p_co):
    '''
    Computes a line between cam_loc and fc and returns the intersection with scene_mesh closest to cam_loc.
    cam_loc: location of the camera.
    scene_mesh: it is a bmesh of all the joint objects in the scene.
    p_co: coordinates of one of the point from the grid in the FOV
    '''
    distances =[]
    # for i, f in enumerate(scene_mesh.faces):
    for f in scene_mesh.faces:
        # if i>4: break
        n = get_face_normal(f.edges[0].verts[0].co, f.edges[0].verts[1].co, f.edges[1].verts[1].co)
        intersect = line_plane_intersection(f.edges[0].verts[0].co, n, cam_loc, cam_loc-p_co)
        try:
            distances.append(intersect.length)
        except:
            distances.append(Vector((0, 0, 0)).length)
            print(intersect)
    return np.nanmin(distances)

def cartesian_to_spherical(x, y, z):
    '''
    It converts the cartesian coordinates to spherical ones.
    Note that the 'elevation' does not exactly correspond to the 'phi' angle usually used.
    Check the source for a visual reference.    
    source: https://it.mathworks.com/help/matlab/ref/cart2sph.html
    '''
    azimuth = np.arctan2(y,x)
    elevation = np.arctan2(z,np.sqrt(x**2 + y**2))
    r = np.sqrt(x**2 + y**2 + z**2)
    return azimuth, elevation, r

def spherical_to_cartesian(azimuth, elevation, r):
    '''
    azimuth: azimuth in radians.
    elevation: elevation in radians.
    r: range.
    source: https://it.mathworks.com/help/matlab/ref/sph2cart.html
    '''
    x = r * np.cos(elevation) * np.cos(azimuth)
    y = r * np.cos(elevation) * np.sin(azimuth)
    z = r * np.sin(elevation)
    return x, y, z

def new_cartesian(cam_loc, h_FOV_shift, v_FOV_shift, d_mul: float = 2):
    '''
    Returns a Vector of the cartesian coordinates of a point inside the FOV and with a distance r from the camera.
    cam_loc: camera cartesian coordinates.
    h_FOV_shift: amount of horizontal shift in radians from the center of the FOV.
    v_FOV_shift: amount of vertival shift in radians from the center of the FOV.
    '''

    # convert the camera location to spherical coordinates
    az_c, el_c, r_c = cartesian_to_spherical(cam_loc[0],cam_loc[1],cam_loc[2])


    # obtain coordinates for the point projected on the plane perpendicular to the x axis
    x = r_c
    hypotenuse = x / np.cos(h_FOV_shift)
    y = np.sin(h_FOV_shift)*hypotenuse
    hypotenuse = x / np.cos(v_FOV_shift)
    z = np.sin(v_FOV_shift)*hypotenuse

    # get the point spherical coordinates if it had y=0. Then, apply a shift to its elevation angle.
    # applying the lateral (y axis) shift allows to avoid the convergence that happens when converging to the poles.
    az_p, el_p, r_p = cartesian_to_spherical(x,0,z*d_mul)
    el_p = el_p - el_c
    x_p,y_p,z_p = spherical_to_cartesian(az_p, el_p, r_p)
    y_p = y_p + y*d_mul

    # now repeat the cart2sph -> sph2cart steps and update the azimuth (or theta) angle.
    az_p, el_p, r_p = cartesian_to_spherical(x_p,y_p,z_p)
    az_p = az_p + az_c + np.pi
    x_p,y_p,z_p = spherical_to_cartesian(az_p, el_p, r_p)

    return Vector((x_p, y_p, z_p))