import bpy
import math as mt
import json
import random, colorsys
import os
import re
import numpy as np
import operator
import copy
from mathutils import Vector
from bpy_extras.object_utils import object_data_add
from io_scene_srt_json.tools import srt_mesh_setup
from io_scene_srt_json.tools.srt_mesh_setup import get_parent_collection

def GetLoopDataPerVertex(mesh, type, layername = None):
    vert_ids = []
    data = []
    for face in mesh.data.polygons:
        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
            if vert_idx not in vert_ids:
                if type == "NORMAL":
                    data.append(list(mesh.data.loops[loop_idx].normal))
                elif type == "TANGENT":
                    data.append(list(mesh.data.loops[loop_idx].tangent))
                elif type == "UV":
                    data.append([mesh.data.uv_layers[layername].data[loop_idx].uv.x, 1-mesh.data.uv_layers[layername].data[loop_idx].uv.y])
                elif type == "VERTEXCOLOR":
                    data.append(mesh.data.vertex_colors[layername].data[loop_idx].color[0])
                vert_ids.append(vert_idx)
    vert_ids, data = (list(t) for t in zip(*sorted(zip(vert_ids, data))))
    return(data)

def getAttributesComponents(attributes):
    components = []
    for i in range(len(attributes)):
        if attributes[i] == "VERTEX_ATTRIB_UNASSIGNED":
            components+= ["VERTEX_COMPONENT_UNASSIGNED"]
        else:
            n = 0
            for j in range(len(attributes[:i])):
                if attributes[j] == attributes[i]:
                    n += 1
            if n == 0:
                components += ["VERTEX_COMPONENT_X"]
            if n == 1:
                components += ["VERTEX_COMPONENT_Y"]
            if n == 2:
                components += ["VERTEX_COMPONENT_Z"]
            if n == 3:
                components += ["VERTEX_COMPONENT_W"]
    return(components)
    
def JoinThem(mesh_names):
    bpy.context.view_layer.objects.active = None
    bpy.ops.object.select_all(action='DESELECT')
    for j in reversed(range(len(mesh_names))):
        bpy.context.view_layer.objects.active = bpy.data.objects[mesh_names[j]]
        bpy.context.active_object.select_set(state=True)
    bpy.ops.object.join()
    # Purge orphan data left by the joining
    override = bpy.context.copy()
    override["area.type"] = ['OUTLINER']
    override["display_mode"] = ['ORPHAN_DATA']
    bpy.ops.outliner.orphans_purge(override)

def write_srt_json(context, filepath):
    wm = bpy.context.window_manager
    wm.EShaderGenerationMode = 'SHADER_GEN_MODE_UNIFIED_SHADERS'
    active_coll = bpy.context.view_layer.active_layer_collection
    parent_colls = []
    main_coll = []
    collision_coll = []
    bb_coll = []
    #horiz_coll = []
    lod_colls = []
    get_parent_collection(active_coll, parent_colls)
    if re.search("SRT Asset", active_coll.name):
        main_coll = active_coll.collection
    elif parent_colls:
        if re.search("SRT Asset", parent_colls[0].name):
            main_coll = parent_colls[0]
            
    if main_coll:
        for col in main_coll.children:
            if re.search("Collision Objects", col.name):
                collision_coll = col
            if re.search("Vertical Billboards", col.name):
                bb_coll = col
            #if re.search("Horizontal Billboard", col.name):
            #    horiz_coll = col
            if re.search("LOD", col.name):
                lod_colls.append(col)
            
        wm.previewLod = False
        # Open main template
        os.chdir(os.path.dirname(__file__))
        with open("templates/mainTemplate.json", 'r', encoding='utf-8') as mainfile:
            srtMain = json.load(mainfile)
            
        #Write Wind
        for k in srtMain["Wind"]:
            if k == 'Params':
                srtMain["Wind"][k] = main_coll[k].to_dict()
            elif k == 'm_abOptions':
                srtMain["Wind"][k] = list(map(bool, main_coll[k].to_list()))
            elif k == 'm_afBranchWindAnchor':
                srtMain["Wind"][k] = main_coll[k].to_list()
            else:
                srtMain["Wind"][k] = main_coll[k]
            
        # Get and Write Collisions #CollisionObjects
        if collision_coll:
            collisionObjects = collision_coll.objects
            if collisionObjects:
                for collisionObject in collisionObjects:
                    bpy.context.view_layer.objects.active = None
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = collisionObject
                    bpy.context.active_object.select_set(state=True)
                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                    with open("templates/collisionTemplate.json", 'r', encoding='utf-8') as collisionfile:
                        srtCollision = json.load(collisionfile)
                        
                    if len(collisionObject.data.materials) <= 1:
                        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
                        collisionObject_vert_coord = collisionObject.data.vertices[0].co
                        collisionObject_radius = (mt.sqrt((collisionObject_vert_coord[0])**2 + (collisionObject_vert_coord[1])**2 + (collisionObject_vert_coord[2])**2))
                        collisionObject_position = collisionObject.matrix_world.translation
                        srtCollision["m_vCenter1"]["x"] = collisionObject_position[0]
                        srtCollision["m_vCenter1"]["y"] = collisionObject_position[1]
                        srtCollision["m_vCenter1"]["z"] = collisionObject_position[2]
                        srtCollision["m_vCenter2"]["x"] = collisionObject_position[0]
                        srtCollision["m_vCenter2"]["y"] = collisionObject_position[1]
                        srtCollision["m_vCenter2"]["z"] = collisionObject_position[2]
                        srtCollision["m_fRadius"] = collisionObject_radius
                        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
                        
                    else:
                        coll_mesh_name = collisionObject.name
                        bpy.ops.mesh.separate(type='MATERIAL')
                        collisionObjects2 = collision_coll.objects
                        coll_mesh_names = []
                        for collisionObject2 in collisionObjects2:
                            if re.search(coll_mesh_name, collisionObject2.name):
                                bpy.context.view_layer.objects.active = None
                                bpy.ops.object.select_all(action='DESELECT')
                                bpy.context.view_layer.objects.active = collisionObject2
                                bpy.context.active_object.select_set(state=True)
                                coll_mesh_names.append(collisionObject2.name)
                                bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
                                if "Material_Sphere1" in collisionObject2.data.materials:
                                    collisionObject_vert_coord = collisionObject2.data.vertices[0].co
                                    collisionObject_radius = (mt.sqrt((collisionObject_vert_coord[0])**2 + (collisionObject_vert_coord[1])**2 + (collisionObject_vert_coord[2])**2))
                                    collisionObject_position = collisionObject2.matrix_world.translation
                                    srtCollision["m_vCenter1"]["x"] = collisionObject_position[0]
                                    srtCollision["m_vCenter1"]["y"] = collisionObject_position[1]
                                    srtCollision["m_vCenter1"]["z"] = collisionObject_position[2]
                                    srtCollision["m_fRadius"] = collisionObject_radius
                                if "Material_Sphere2" in collisionObject2.data.materials:
                                    collisionObject_position = collisionObject2.matrix_world.translation
                                    srtCollision["m_vCenter2"]["x"] = collisionObject_position[0]
                                    srtCollision["m_vCenter2"]["y"] = collisionObject_position[1]
                                    srtCollision["m_vCenter2"]["z"] = collisionObject_position[2]
                            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
                        JoinThem(coll_mesh_names)
                    srtMain["CollisionObjects"].append(srtCollision)
            else:
                srtMain.pop("CollisionObjects")
        else:
            srtMain.pop("CollisionObjects")
            
        # Get and Write Vertical Billboards #VerticalBillboards
        if bb_coll:
            billboard_uvs = []
            billboard_rotated = []
            billboard_cutout_verts = []
            billboard_cutout_indices = []
            billboards = re.findall(r"Mesh_billboard\d+\.?\d*", str([x.name for x in bb_coll.objects]))
            cutout = re.findall(r"Mesh_cutout\.?\d*", str([x.name for x in bb_coll.objects]))
            if billboards:
                for billboard in billboards:
                    billboard_uv_x = []
                    billboard_uv_y = []
                    bb = bb_coll.objects[billboard]
                    bpy.context.view_layer.objects.active = None
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = bb
                    bpy.context.active_object.select_set(state=True)
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                    for face in bb.data.polygons:
                        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                            billboard_uv_x.append(bb.data.uv_layers[0].data[loop_idx].uv.x)
                            billboard_uv_y.append(bb.data.uv_layers[0].data[loop_idx].uv.y)
                    billboard_uv_sum = list(map(operator.add, billboard_uv_x, billboard_uv_y))
                    if billboard_uv_sum.index(min(billboard_uv_sum)) == 0:
                        billboard_rotated.append(0)
                        billboard_uvs.append(billboard_uv_x[0])
                        billboard_uvs.append(1-billboard_uv_y[0])
                        billboard_uvs.append(billboard_uv_x[2] - billboard_uv_x[0])
                        billboard_uvs.append((1-billboard_uv_y[2]) - (1-billboard_uv_y[0]))
                    elif billboard_uv_sum.index(min(billboard_uv_sum)) == 2:
                        billboard_rotated.append(1)
                        billboard_uvs.append(billboard_uv_x[0])
                        billboard_uvs.append(1-billboard_uv_y[2])
                        billboard_uvs.append(billboard_uv_x[2] - billboard_uv_x[0])
                        billboard_uvs.append((1-billboard_uv_y[0]) - (1-billboard_uv_y[2]))
            
            if cutout:            
                cut = bb_coll.objects[cutout[0]]
                billboard_cutout_nverts = len(cut.data.vertices)
                for vert in cut.data.vertices:
                    billboard_cutout_verts.append((vert.co.x - -wm.FWidth/2)/wm.FWidth)
                    billboard_cutout_verts.append((vert.co.z - wm.FBottomPos)/(wm.FTopPos - wm.FBottomPos))
                for face in cut.data.polygons:
                    for vertex in face.vertices:
                        billboard_cutout_indices.append(vertex)
                       
            srtMain["VerticalBillboards"]["FWidth"] = wm.FWidth
            srtMain["VerticalBillboards"]["FTopPos"] = wm.FTopPos
            srtMain["VerticalBillboards"]["FBottomPos"] = wm.FBottomPos
            srtMain["VerticalBillboards"]["NNumBillboards"] = wm.NNumBillboards
            srtMain["VerticalBillboards"]["PTexCoords"] = billboard_uvs
            srtMain["VerticalBillboards"]["PRotated"] = billboard_rotated
            srtMain["VerticalBillboards"]["NNumCutoutVertices"] = billboard_cutout_nverts
            srtMain["VerticalBillboards"]["PCutoutVertices"] = billboard_cutout_verts
            srtMain["VerticalBillboards"]["NNumCutoutIndices"] = len(billboard_cutout_indices)
            srtMain["VerticalBillboards"]["PCutoutIndices"] = billboard_cutout_indices
            
        #Get and Write Horizontal Billboard #HorizontalBillboard    #Unsupported by RedEngine
                                                                    # But remains here in case
                                                                    # I decide to support others
                                                                    # shader generation mode
        #if horiz_coll:
        #    horiz_bb_verts = []
        #    horiz_bb_uvs = []
        #    horiz_bb = horiz_coll.objects[0]
        #    bpy.context.view_layer.objects.active = None
        #    bpy.ops.object.select_all(action='DESELECT')
        #    bpy.context.view_layer.objects.active = horiz_bb
        #    bpy.context.active_object.select_set(state=True)
        #    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        #    for vert in horiz_bb.data.vertices:
        #        horiz_bb_verts.append(vert.co)
        #    for face in horiz_bb.data.polygons:
        #        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
        #            horiz_bb_uvs.append(horiz_bb.data.uv_layers[0].data[loop_idx].uv.x)
        #            horiz_bb_uvs.append(1 - horiz_bb.data.uv_layers[0].data[loop_idx].uv.y)
        #    srtMain["HorizontalBillboard"]["BPresent"] = True
        #    srtMain["HorizontalBillboard"]["AfTexCoords"] = horiz_bb_uvs
        #    for i in range(4):
        #        srtMain["HorizontalBillboard"]["AvPositions"][i]["x"] = horiz_bb_verts[i][0]
        #        srtMain["HorizontalBillboard"]["AvPositions"][i]["y"] = horiz_bb_verts[i][1]
        #        srtMain["HorizontalBillboard"]["AvPositions"][i]["z"] = horiz_bb_verts[i][2]
                
        #Get and Write Billboard Material #ABillboardRenderStateMain
        bb_textures_names = []
        if bb_coll: #or horiz_coll:
            for k in srtMain["Geometry"]["ABillboardRenderStateMain"]:
                if hasattr(wm, k):
                    srtMain["Geometry"]["ABillboardRenderStateMain"][k] = getattr(wm, k)
                    if k in ["VAmbientColor", "VDiffuseColor", "VSpecularColor", "VTransmissionColor"]:
                        srtMain["Geometry"]["ABillboardRenderStateMain"][k] = {'x':getattr(wm, k)[0], 'y':getattr(wm, k)[1], 'z':getattr(wm, k)[2]}
            
            srtMain["Geometry"]["ABillboardRenderStateMain"]["BUsedAsGrass"] = False
            srtMain["Geometry"]["ABillboardRenderStateMain"]["ELodMethod"] = "LOD_METHOD_POP"
            srtMain["Geometry"]["ABillboardRenderStateMain"]["EShaderGenerationMode"] = "SHADER_GEN_MODE_STANDARD"
            srtMain["Geometry"]["ABillboardRenderStateMain"]["EDetailLayer"] = "EFFECT_OFF"
            srtMain["Geometry"]["ABillboardRenderStateMain"]["EBranchSeamSmoothing"] = "EFFECT_OFF"
            srtMain["Geometry"]["ABillboardRenderStateMain"]["EWindLod"] = "WIND_LOD_NONE"
            srtMain["Geometry"]["ABillboardRenderStateMain"]["BBranchesPresent"] = False
            srtMain["Geometry"]["ABillboardRenderStateMain"]["BFrondsPresent"] = False
            srtMain["Geometry"]["ABillboardRenderStateMain"]["BLeavesPresent"] = False
            srtMain["Geometry"]["ABillboardRenderStateMain"]["BFacingLeavesPresent"] = False
            srtMain["Geometry"]["ABillboardRenderStateMain"]["BRigidMeshesPresent"] = False
            #if horiz_coll:
            #    srtMain["Geometry"]["ABillboardRenderStateMain"]["BHorzBillboard"] = True
                
            for k in ["diffuseTexture", "normalTexture", "specularTexture", "detailTexture", "detailNormalTexture"]:
                tex = getattr(wm, k)
                if tex:
                    bb_textures_names.append(tex.name)
                    if k == "diffuseTexture":
                        srtMain["Geometry"]["ABillboardRenderStateMain"]["ApTextures"][0]["Val"] = tex.name
                    if k == "normalTexture":
                        srtMain["Geometry"]["ABillboardRenderStateMain"]["ApTextures"][1]["Val"] = tex.name
                    if k == "detailTexture":
                        srtMain["Geometry"]["ABillboardRenderStateMain"]["ApTextures"][2]["Val"] = tex.name
                    if k == "detailNormalTexture":
                        srtMain["Geometry"]["ABillboardRenderStateMain"]["ApTextures"][3]["Val"] = tex.name
                    if k == "specularTexture":
                        srtMain["Geometry"]["ABillboardRenderStateMain"]["ApTextures"][4]["Val"] = tex.name
                        srtMain["Geometry"]["ABillboardRenderStateMain"]["ApTextures"][5]["Val"] = tex.name
                        
            #Write ABillboardRenderStateShadow
            srtMain["Geometry"]["ABillboardRenderStateShadow"] = copy.deepcopy(srtMain["Geometry"]["ABillboardRenderStateMain"])
            for i in range(1, len(srtMain["Geometry"]["ABillboardRenderStateShadow"]["ApTextures"])):
                srtMain["Geometry"]["ABillboardRenderStateShadow"]["ApTextures"][i]["Val"] = ""
            srtMain["Geometry"]["ABillboardRenderStateShadow"]["ERenderPass"] = "RENDER_PASS_SHADOW_CAST"
            srtMain["Geometry"]["ABillboardRenderStateShadow"]["BFadeToBillboard"] = False  
            
        #Get and Write Meshes#
        lodsNum = 0
        mesh_index = 0
        meshesNum = 0
        textures_names = []
        if lod_colls:
            for col in lod_colls:
                if col.objects:
                    with open("templates/lodTemplate.json", 'r', encoding='utf-8') as lodfile:
                        srtLod = json.load(lodfile)
                    # Get lodsNum
                    lodsNum += 1
                    for mesh in col.objects:
                        bpy.context.view_layer.objects.active = None
                        bpy.ops.object.select_all(action='DESELECT')
                        bpy.context.view_layer.objects.active = mesh
                        bpy.context.active_object.select_set(state=True)
                        # Triangulate faces
                        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                        bpy.ops.mesh.select_all(action="SELECT")
                        bpy.ops.mesh.quads_convert_to_tris(quad_method='SHORTEST_DIAGONAL', ngon_method='BEAUTY')
                        bpy.ops.mesh.select_all(action="DESELECT")
                        bpy.ops.object.mode_set(mode='OBJECT')
                        # Split by materials
                        bpy.ops.mesh.separate(type='MATERIAL')
                    mesh_names = []
                    for mesh in col.objects:
                        with open("templates/drawTemplate.json", 'r', encoding='utf-8') as drawfile:
                            srtDraw = json.load(drawfile)
                        bpy.context.view_layer.objects.active = None
                        bpy.ops.object.select_all(action='DESELECT')
                        bpy.context.view_layer.objects.active = mesh
                        bpy.context.active_object.select_set(state=True)
                        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                        if wm.BUsedAsGrass:
                            wm.BBranchesPresent = False
                            wm.BFrondsPresent = True
                            wm.BLeavesPresent = True
                            wm.BFacingLeavesPresent = True
                            wm.BRigidMeshesPresent = True
                        if "DiffuseUV" in mesh.data.uv_layers:
                            mesh.data.uv_layers.active = mesh.data.uv_layers["DiffuseUV"]
                        mesh.data.calc_normals_split()
                        if mesh.data.uv_layers:
                            mesh.data.calc_tangents()
                        if not wm.BRigidMeshesPresent or (wm.BFacingLeavesPresent and wm.BRigidMeshesPresent): #Dont export pure rigid meshes because not supported by RedEngine
                            # Get data per vertex
                            verts = []
                            verts_lod = []
                            normals = []
                            uvs_diff = []
                            uvs_det = []
                            geom_types = []
                            wind_weight1 = []
                            wind_weight2 = []
                            wind_normal1 = []
                            wind_normal2 = []
                            wind_extra1 = []
                            wind_extra2 = []
                            wind_extra3 = []
                            wind_flags = []
                            leaf_card_corners = []
                            leaf_card_lod_scalars = []
                            leaf_anchor_points = []
                            branches_seam_diff = []
                            branches_seam_det = []
                            seam_blending = []
                            tangents = []
                            ambients = []
                            faces = []
                            mesh_names.append(mesh.name)
                            for vert in mesh.data.vertices:
                                # Verts' position
                                verts.append(list(vert.undeformed_co))
                                # Verts' lod position
                                if 'vertexLodPosition' in mesh.data.attributes:
                                    verts_lod.append(list(mesh.data.attributes['vertexLodPosition'].data[vert.index].vector))
                                # Leaf Card Corner
                                if 'leafCardCorner' in mesh.data.attributes:
                                    leaf_card_corners.append(list(mesh.data.attributes['leafCardCorner'].data[vert.index].vector))
                                    leaf_card_coord_z = leaf_card_corners[-1][1]
                                    leaf_card_corners[-1].pop(1)
                                    leaf_card_corners[-1].append(leaf_card_coord_z)
                                # Leaf Card LOD Scalar
                                if 'leafCardLodScalar' in mesh.data.attributes:
                                    leaf_card_lod_scalars.append(mesh.data.attributes['leafCardLodScalar'].data[vert.index].value)
                                # Leaf Anchor Point
                                if 'leafAnchorPoint' in mesh.data.attributes:
                                    leaf_anchor_points.append(list(mesh.data.attributes['leafAnchorPoint'].data[vert.index].vector))
                                # Vertex Colors (Ambient Occlusion and Seam Blending)
                                if "AmbientOcclusion" in mesh.data.color_attributes:
                                    ambients.append(mesh.data.color_attributes['AmbientOcclusion'].data[vert.index].color[0])
                                if "SeamBlending" in mesh.data.color_attributes:
                                    seam_blending.append(mesh.data.color_attributes['SeamBlending'].data[vert.index].color[0])
                                # Wind data and Geom Type
                                #Add values if missing just to make the exporter more robust
                                if not vert.groups:
                                    if geom_types:
                                        mesh.vertex_groups["GeomType"].add([vert.index], ((1 + random.choice(geom_types))/5), 'REPLACE')
                                    if wind_weight1:
                                        mesh.vertex_groups["WindWeight1"].add([vert.index], 0, 'REPLACE')
                                    if wind_weight2:
                                        mesh.vertex_groups["WindWeight2"].add([vert.index], 0, 'REPLACE')
                                    if wind_normal1:
                                        mesh.vertex_groups["WindNormal1"].add([vert.index], 0, 'REPLACE')
                                    if wind_normal2:
                                        mesh.vertex_groups["WindNormal2"].add([vert.index], 0, 'REPLACE')
                                    if wind_extra1:
                                        mesh.vertex_groups["WindExtra1"].add([vert.index], 0, 'REPLACE')
                                    if wind_extra2:
                                        mesh.vertex_groups["WindExtra2"].add([vert.index], 0, 'REPLACE')
                                    if wind_extra3:
                                        mesh.vertex_groups["WindExtra3"].add([vert.index], 0, 'REPLACE')
                                    if wind_flags:
                                        mesh.vertex_groups["WindFlag"].add([vert.index], random.choice(wind_flags), 'REPLACE')
                                for g in vert.groups:
                                    if mesh.vertex_groups[g.group].name == "GeomType":
                                        if wm.BUsedAsGrass:
                                            geom_types.append(1) 
                                        else:
                                            geom_types.append(int(g.weight*5-1))
                                    if mesh.vertex_groups[g.group].name == "WindWeight1":
                                        wind_weight1.append(g.weight)
                                    if mesh.vertex_groups[g.group].name == "WindWeight2":
                                        wind_weight2.append(g.weight)
                                    if mesh.vertex_groups[g.group].name == "WindNormal1":
                                        wind_normal1.append(g.weight*16)
                                    if mesh.vertex_groups[g.group].name == "WindNormal2":
                                        wind_normal2.append(g.weight*16)
                                    if mesh.vertex_groups[g.group].name == "WindExtra1":
                                        wind_extra1.append(g.weight*16)
                                    if mesh.vertex_groups[g.group].name == "WindExtra2":
                                        wind_extra2.append(g.weight)
                                    if mesh.vertex_groups[g.group].name == "WindExtra3":
                                        wind_extra3.append(g.weight*2)
                                    if mesh.vertex_groups[g.group].name == "WindFlag":
                                        wind_flags.append(g.weight)
                                       
                            # Faces
                            for face in mesh.data.polygons:
                                for vert in face.vertices:
                                    faces.append(vert)
                                    
                            # Verts' normal and tangent
                            normals = GetLoopDataPerVertex(mesh, "NORMAL")
                            tangents = GetLoopDataPerVertex(mesh, "TANGENT")
                            
                            # UVs
                            if "DiffuseUV" in mesh.data.uv_layers:
                                uvs_diff = GetLoopDataPerVertex(mesh, "UV", "DiffuseUV")
                            if "DetailUV" in mesh.data.uv_layers:
                                uvs_det = GetLoopDataPerVertex(mesh, "UV", "DetailUV")
                            if "SeamDiffuseUV" in mesh.data.uv_layers:
                                branches_seam_diff = GetLoopDataPerVertex(mesh, "UV", "SeamDiffuseUV")
                            if "SeamDetailUV" in mesh.data.uv_layers:
                                branches_seam_det = GetLoopDataPerVertex(mesh, "UV", "SeamDetailUV")
                                
                            # Write data per vertex
                            properties = ["START"]
                            components = []
                            offsets = []
                            formats = []
                            attributes = []
                            attributes_components = []
                            num_attrib = 0
                            attrib_name0 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name1 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name2 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name3 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name4 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name5 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name6 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name7 = "VERTEX_ATTRIB_UNASSIGNED"
                            attrib_name8 = "VERTEX_ATTRIB_UNASSIGNED"
                            for i in range(len(verts)):
                                with open("templates/vertTemplate.json", 'r', encoding='utf-8') as vertfile:
                                    srtVert = json.load(vertfile)
                                offset = 0
                                # Vert position
                                if verts:
                                    srtVert["VertexProperties"][0]["ValueCount"] =  3
                                    srtVert["VertexProperties"][0]["FloatValues"] =  verts[i]
                                    srtVert["VertexProperties"][0]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][0]["ValueOffsets"] = [offset, offset +2, offset + 4]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_POSITION"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset +2, offset + 4]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        attrib_name0 = "VERTEX_ATTRIB_"+str(num_attrib)
                                        num_attrib += 1
                                        attributes += [attrib_name0]*3
                                    offset += 6
                                # Lod position
                                if verts_lod and (not wm.BFacingLeavesPresent or (wm.BFacingLeavesPresent and wm.BLeavesPresent)):
                                    srtVert["VertexProperties"][3]["ValueCount"] =  3
                                    srtVert["VertexProperties"][3]["FloatValues"] =  verts_lod[i]
                                    srtVert["VertexProperties"][3]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][3]["ValueOffsets"] = [offset, offset + 6, offset + 8]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_LOD_POSITION"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset + 6, offset + 8]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        if attrib_name0 == "VERTEX_ATTRIB_UNASSIGNED":
                                            attrib_name0 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            num_attrib += 1
                                        attrib_name1 = "VERTEX_ATTRIB_"+str(num_attrib)
                                        num_attrib += 1
                                        attributes += [attrib_name0, attrib_name1, attrib_name1]
                                    offset += 6
                                # Leaf Card Corner
                                if leaf_card_corners and wm.BFacingLeavesPresent and not wm.BLeavesPresent:
                                    srtVert["VertexProperties"][5]["ValueCount"] =  3
                                    srtVert["VertexProperties"][5]["FloatValues"] =  leaf_card_corners[i]
                                    srtVert["VertexProperties"][5]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][5]["ValueOffsets"] = [offset, offset + 6, offset + 8]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_LEAF_CARD_CORNER"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset + 6, offset + 8]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        if attrib_name0 == "VERTEX_ATTRIB_UNASSIGNED":
                                            attrib_name0 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            num_attrib += 1
                                        if attrib_name1 == "VERTEX_ATTRIB_UNASSIGNED":
                                            attrib_name1 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            num_attrib += 1
                                        attributes += [attrib_name0, attrib_name1, attrib_name1]
                                    offset += 6
                                # Diffuse UV
                                if uvs_diff:
                                    srtVert["VertexProperties"][1]["ValueCount"] =  2
                                    srtVert["VertexProperties"][1]["FloatValues"] =  uvs_diff[i]
                                    srtVert["VertexProperties"][1]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][1]["ValueOffsets"] = [offset-4, offset -2]
                                    if properties[-1] != "END":
                                        properties [-2:-2] = ["VERTEX_PROPERTY_DIFFUSE_TEXCOORDS"] * 2
                                        components [-2:-2] = ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y"]
                                        offsets [-2:-2] = [offset-4, offset -2]
                                        formats [-2:-2] = ["VERTEX_FORMAT_HALF_FLOAT"] * 2
                                        if attrib_name1 == "VERTEX_ATTRIB_UNASSIGNED":
                                            attrib_name1 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            num_attrib += 1
                                        attributes [-2:-2] = [attrib_name1]*2
                                    offset += 4
                                # Geometry Type
                                if geom_types[0] != -1 and ((not wm.BFacingLeavesPresent and not wm.BLeavesPresent) or (wm.BFacingLeavesPresent and wm.BLeavesPresent)):
                                    srtVert["VertexProperties"][4]["ValueCount"] =  1
                                    srtVert["VertexProperties"][4]["FloatValues"] =  [geom_types[i]]
                                    srtVert["VertexProperties"][4]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][4]["ValueOffsets"] = [offset]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_GEOMETRY_TYPE_HINT"]
                                        components += ["VERTEX_COMPONENT_X"]
                                        offsets += [offset]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"]
                                        attrib_name2 = "VERTEX_ATTRIB_"+str(num_attrib)
                                        num_attrib += 1
                                        attributes += [attrib_name2]
                                    offset += 2
                                ### Leaf Card Corner FOR GRASS ###
                                if leaf_card_corners and wm.BFacingLeavesPresent and wm.BLeavesPresent:
                                    srtVert["VertexProperties"][5]["ValueCount"] =  3
                                    srtVert["VertexProperties"][5]["FloatValues"] =  leaf_card_corners[i]
                                    srtVert["VertexProperties"][5]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][5]["ValueOffsets"] = [offset, offset + 2, offset + 4]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_LEAF_CARD_CORNER"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset + 2, offset + 4]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        if attrib_name2 == "VERTEX_ATTRIB_UNASSIGNED":
                                            attrib_name2 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            num_attrib += 1
                                        attributes += [attrib_name2, attrib_name2, attrib_name2]
                                    offset += 6
                                # Leaf Card Lod Scalar
                                if leaf_card_lod_scalars and wm.BFacingLeavesPresent:
                                    srtVert["VertexProperties"][6]["ValueCount"] =  1
                                    srtVert["VertexProperties"][6]["FloatValues"] =  [leaf_card_lod_scalars[i]]
                                    srtVert["VertexProperties"][6]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][6]["ValueOffsets"] = [offset]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_LEAF_CARD_LOD_SCALAR"]
                                        components += ["VERTEX_COMPONENT_X"]
                                        offsets += [offset]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"]
                                        if wm.BLeavesPresent: #Exception for Grass
                                            if attrib_name3 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name3 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name3]
                                        else:
                                            if attrib_name2 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name2 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name2]
                                    offset += 2
                                ### Wind Branch Data FOR LEAVES ###
                                if wind_weight1 and wind_weight2 and wind_normal1 and wind_normal2 and not wm.BFacingLeavesPresent and wm.BLeavesPresent:
                                    srtVert["VertexProperties"][8]["ValueCount"] =  4
                                    srtVert["VertexProperties"][8]["FloatValues"] =  [wind_weight1[i], wind_normal1[i], wind_weight2[i], wind_normal2[i]]
                                    srtVert["VertexProperties"][8]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][8]["ValueOffsets"] = [offset, offset +2, offset + 4, offset + 6]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_WIND_BRANCH_DATA"] * 4
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z", "VERTEX_COMPONENT_W"]
                                        offsets += [offset, offset +2, offset + 4, offset + 6]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 4
                                        attrib_name2 = "VERTEX_ATTRIB_"+str(num_attrib)
                                        attributes += [attrib_name2]*4
                                        num_attrib += 1
                                    offset += 8
                                # Wind Extra Data
                                if wind_extra1 and wind_extra2 and wind_extra3 and not wm.BBranchesPresent:
                                    srtVert["VertexProperties"][9]["ValueCount"] =  3
                                    srtVert["VertexProperties"][9]["FloatValues"] =  [wind_extra1[i], wind_extra2[i], wind_extra3[i]]
                                    srtVert["VertexProperties"][9]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][9]["ValueOffsets"] = [offset, offset +2, offset + 4]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_WIND_EXTRA_DATA"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset +2, offset + 4]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        if wm.BLeavesPresent: #Exception for Grass and Leaves
                                            if attrib_name3 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name3 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name3]*3
                                        else:
                                            if attrib_name2 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name2 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name2]*3
                                    offset += 6
                                # Branch Seam Diffuse
                                if branches_seam_diff and seam_blending and wm.BBranchesPresent:
                                    srtVert["VertexProperties"][13]["ValueCount"] =  3
                                    srtVert["VertexProperties"][13]["FloatValues"] =  [branches_seam_diff[i][0], branches_seam_diff[i][1], seam_blending[i]]
                                    srtVert["VertexProperties"][13]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][13]["ValueOffsets"] = [offset, offset +2, offset + 4]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_BRANCH_SEAM_DIFFUSE"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset +2, offset + 4]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        if attrib_name2 == "VERTEX_ATTRIB_UNASSIGNED":
                                            attrib_name2 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            num_attrib += 1
                                        attributes += [attrib_name2]*3
                                    offset += 6
                                # Wind Branch Data
                                if wind_weight1 and wind_weight2 and wind_normal1 and wind_normal2 and (not wm.BLeavesPresent or (wm.BFacingLeavesPresent and wm.BLeavesPresent)):
                                    srtVert["VertexProperties"][8]["ValueCount"] =  4
                                    srtVert["VertexProperties"][8]["FloatValues"] =  [wind_weight1[i], wind_normal1[i], wind_weight2[i], wind_normal2[i]]
                                    srtVert["VertexProperties"][8]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][8]["ValueOffsets"] = [offset, offset +2, offset + 4, offset + 6]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_WIND_BRANCH_DATA"] * 4
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z", "VERTEX_COMPONENT_W"]
                                        offsets += [offset, offset +2, offset + 4, offset + 6]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 4
                                        if wm.BLeavesPresent and wm.BFacingLeavesPresent: #Exception for Grass
                                            attrib_name4 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name4]*4
                                            num_attrib += 1
                                        else:
                                            attrib_name3 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name3]*4
                                            num_attrib += 1
                                    offset += 8
                                # Branch Seam Detail
                                if branches_seam_det and seam_blending and wm.BBranchesPresent:
                                    srtVert["VertexProperties"][14]["ValueCount"] =  2
                                    srtVert["VertexProperties"][14]["FloatValues"] =  branches_seam_det[i]
                                    srtVert["VertexProperties"][14]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][14]["ValueOffsets"] = [offset, offset +2]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_BRANCH_SEAM_DETAIL"] * 2
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y"]
                                        offsets += [offset, offset +2]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 2
                                        attrib_name4 = "VERTEX_ATTRIB_"+str(num_attrib)
                                        attributes += [attrib_name4]*2
                                        num_attrib += 1
                                    offset += 4
                                # Detail UV
                                if uvs_det and wm.BBranchesPresent:
                                    srtVert["VertexProperties"][15]["ValueCount"] =  2
                                    srtVert["VertexProperties"][15]["FloatValues"] =  uvs_det[i]
                                    srtVert["VertexProperties"][15]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][15]["ValueOffsets"] = [offset, offset +2]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_DETAIL_TEXCOORDS"] * 2
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y"]
                                        offsets += [offset, offset +2]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 2
                                        if attrib_name4 == "VERTEX_ATTRIB_UNASSIGNED":
                                            attrib_name4 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            num_attrib += 1
                                        attributes += [attrib_name4]*2
                                    offset += 4
                                # Wind Flags
                                if wind_flags and ((wm.BFacingLeavesPresent and not wm.BLeavesPresent) or (not wm.BFacingLeavesPresent and wm.BLeavesPresent)):
                                    srtVert["VertexProperties"][10]["ValueCount"] =  1
                                    srtVert["VertexProperties"][10]["FloatValues"] =  [wind_flags[i]]
                                    srtVert["VertexProperties"][10]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][10]["ValueOffsets"] = [offset]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_WIND_FLAGS"]
                                        components += ["VERTEX_COMPONENT_X"]
                                        offsets += [offset]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"]
                                        if wm.BLeavesPresent and not wm.BFacingLeavesPresent: # Exception for Leaves
                                            if attrib_name3 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name3 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name3]
                                        elif wm.BFacingLeavesPresent and not wm.BLeavesPresent: # Exception for Facing Leaves
                                            if attrib_name4 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name4 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name4]
                                    offset += 2
                                # Leaf Anchor Point
                                if leaf_anchor_points and ((wm.BLeavesPresent and wm.BFacingLeavesPresent) or (wm.BLeavesPresent and not wm.BFacingLeavesPresent)):
                                    srtVert["VertexProperties"][11]["ValueCount"] =  3
                                    srtVert["VertexProperties"][11]["FloatValues"] =  leaf_anchor_points[i]
                                    srtVert["VertexProperties"][11]["PropertyFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                                    srtVert["VertexProperties"][11]["ValueOffsets"] = [offset, offset +2, offset + 4]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_LEAF_ANCHOR_POINT"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset +2, offset + 4]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        if wm.BLeavesPresent and not wm.BFacingLeavesPresent: #Exception for Leaves
                                            attrib_name4 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name4]*3
                                            num_attrib += 1
                                        elif wm.BLeavesPresent and wm.BFacingLeavesPresent: #Exception for Grass
                                            attrib_name5 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name5]*3
                                            num_attrib += 1
                                    offset += 6
                                # half float padding
                                if len(properties[1:])/4 != int(len(properties[1:])/4) and properties[-1] != "END":
                                    if (len(properties[1:])/4) % 1 == 0.25:
                                        properties += ["VERTEX_PROPERTY_PAD", "VERTEX_PROPERTY_UNASSIGNED","VERTEX_PROPERTY_UNASSIGNED"]
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_UNASSIGNED", "VERTEX_COMPONENT_UNASSIGNED"]
                                        offsets += [offset, 0, 0]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"] * 3
                                        attributes += ["VERTEX_ATTRIB_UNASSIGNED"]*3
                                        offset += 2
                                    elif (len(properties[1:])/4) % 1 == 0.5:
                                        properties += ["VERTEX_PROPERTY_UNASSIGNED"]*2
                                        components += ["VERTEX_COMPONENT_UNASSIGNED"]*2
                                        offsets += [0,0]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"]*2
                                        attributes += ["VERTEX_ATTRIB_UNASSIGNED"]*2
                                    elif (len(properties[1:])/4) % 1 == 0.75:
                                        properties += ["VERTEX_PROPERTY_PAD"]
                                        components += ["VERTEX_COMPONENT_X"]
                                        offsets += [offset]
                                        formats += ["VERTEX_FORMAT_HALF_FLOAT"]
                                        attributes += ["VERTEX_ATTRIB_UNASSIGNED"]
                                        offset += 2
                                # Normals
                                if normals:
                                    srtVert["VertexProperties"][2]["ValueCount"] =  3
                                    srtVert["VertexProperties"][2]["FloatValues"] =  normals[i]
                                    srtVert["VertexProperties"][2]["PropertyFormat"] = "VERTEX_FORMAT_BYTE"
                                    srtVert["VertexProperties"][2]["ValueOffsets"] = [offset, offset +1, offset + 2]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_NORMAL"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset +1, offset +2]
                                        formats += ["VERTEX_FORMAT_BYTE"] * 3
                                        if wm.BLeavesPresent and wm.BFacingLeavesPresent: #Exception for Grass
                                            attrib_name6 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name6]*3
                                            num_attrib += 1
                                        else:
                                            attrib_name5 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name5]*3
                                            num_attrib += 1
                                    offset += 3
                                # Ambient Occlusion
                                if ambients:
                                    srtVert["VertexProperties"][18]["ValueCount"] =  1
                                    srtVert["VertexProperties"][18]["FloatValues"] =  [ambients[i]]
                                    srtVert["VertexProperties"][18]["PropertyFormat"] = "VERTEX_FORMAT_BYTE"
                                    srtVert["VertexProperties"][18]["ValueOffsets"] = [offset]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_AMBIENT_OCCLUSION"]
                                        components += ["VERTEX_COMPONENT_X"]
                                        offsets += [offset]
                                        formats += ["VERTEX_FORMAT_BYTE"]
                                        if wm.BLeavesPresent and wm.BFacingLeavesPresent: #Exception for Grass
                                            if attrib_name6 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name6 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name6]
                                        else:
                                            if attrib_name5 == "VERTEX_ATTRIB_UNASSIGNED":
                                                attrib_name5 = "VERTEX_ATTRIB_"+str(num_attrib)
                                                num_attrib += 1
                                            attributes += [attrib_name5]
                                    offset += 1
                                # Tangents
                                if tangents:
                                    srtVert["VertexProperties"][16]["ValueCount"] =  3
                                    srtVert["VertexProperties"][16]["FloatValues"] =  tangents[i]
                                    srtVert["VertexProperties"][16]["PropertyFormat"] = "VERTEX_FORMAT_BYTE"
                                    srtVert["VertexProperties"][16]["ValueOffsets"] = [offset, offset +1, offset + 2]
                                    if properties[-1] != "END":
                                        properties += ["VERTEX_PROPERTY_TANGENT"] * 3
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_Y", "VERTEX_COMPONENT_Z"]
                                        offsets += [offset, offset +1, offset +2]
                                        formats += ["VERTEX_FORMAT_BYTE"] * 3
                                        if wm.BLeavesPresent and wm.BFacingLeavesPresent: #Exception for Grass
                                            attrib_name7 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name7]*3
                                            num_attrib += 1
                                        else:
                                            attrib_name6 = "VERTEX_ATTRIB_"+str(num_attrib)
                                            attributes += [attrib_name6]*3
                                            num_attrib += 1
                                    offset += 3
                                # byte padding
                                if len(properties[1:])/4 != int(len(properties[1:])/4) and properties[-1] != "END":
                                    if (len(properties[1:])/4) % 1 == 0.25:
                                        properties += ["VERTEX_PROPERTY_PAD", "VERTEX_PROPERTY_UNASSIGNED","VERTEX_PROPERTY_UNASSIGNED"]
                                        components += ["VERTEX_COMPONENT_X", "VERTEX_COMPONENT_UNASSIGNED", "VERTEX_COMPONENT_UNASSIGNED"]
                                        offsets += [offset, 0, 0]
                                        formats += ["VERTEX_FORMAT_BYTE"] * 3
                                        attributes += ["VERTEX_ATTRIB_UNASSIGNED"]*3
                                        offset += 1
                                    elif (len(properties[1:])/4) % 1 == 0.5:
                                        properties += ["VERTEX_PROPERTY_UNASSIGNED"]*2
                                        components += ["VERTEX_COMPONENT_UNASSIGNED"]*2
                                        offsets += [0,0]
                                        formats += ["VERTEX_FORMAT_BYTE"]*2
                                        attributes += ["VERTEX_ATTRIB_UNASSIGNED"]*2
                                    elif (len(properties[1:])/4) % 1 == 0.75:
                                        properties += ["VERTEX_PROPERTY_PAD"]
                                        components += ["VERTEX_COMPONENT_X"]
                                        offsets += [offset]
                                        formats += ["VERTEX_FORMAT_BYTE"]
                                        attributes += ["VERTEX_ATTRIB_UNASSIGNED"]
                                        offset += 1
                                
                                if properties[-1] != "END": 
                                    offset_final = offset
                                
                                while len(properties) < 65 and properties[-1] != "END":
                                    properties += ["VERTEX_PROPERTY_UNASSIGNED"]
                                    components += ["VERTEX_COMPONENT_UNASSIGNED"]
                                    offsets += [0]
                                    formats += ["VERTEX_FORMAT_UNASSIGNED"]
                                    attributes += ["VERTEX_ATTRIB_UNASSIGNED"]
                                
                                properties.append("END")
                                
                                srtDraw["PVertexData"].append(srtVert)
                            
                            # Write data per mesh
                            srtDraw["NNumVertices"] = len(verts)
                            srtDraw["NRenderStateIndex"] = mesh_index
                            mesh_index += 1
                            srtDraw["NNumIndices"] = len(faces)
                            srtDraw["PIndexData"] = faces
                            srtDraw["PRenderState"]["SVertexDecl"]["UiVertexSize"] = offset_final
                            
                            # Write mesh material
                            for k in srtDraw["PRenderState"]:
                                if hasattr(wm, k):
                                    srtDraw["PRenderState"][k] = getattr(wm, k)
                                    if k in ["VAmbientColor", "VDiffuseColor", "VSpecularColor", "VTransmissionColor"]:
                                        srtDraw["PRenderState"][k] = {'x':getattr(wm, k)[0], 'y':getattr(wm, k)[1], 'z':getattr(wm, k)[2]}
                            if col == lod_colls[-1]:  
                                if bb_coll: #or horiz_coll:
                                    srtDraw["PRenderState"]["BFadeToBillboard"] = True
                                    
                            # Write mesh textures
                            for k in ["diffuseTexture", "normalTexture", "specularTexture", "detailTexture", "detailNormalTexture"]:
                                tex = getattr(wm, k)
                                if tex:
                                    textures_names.append(tex.name)
                                    if k == "diffuseTexture":
                                        srtDraw["PRenderState"]["ApTextures"][0]["Val"] = tex.name
                                    if k == "normalTexture":
                                        srtDraw["PRenderState"]["ApTextures"][1]["Val"] = tex.name
                                    if k == "detailTexture":
                                        srtDraw["PRenderState"]["ApTextures"][2]["Val"] = tex.name
                                    if k == "detailNormalTexture":
                                        srtDraw["PRenderState"]["ApTextures"][3]["Val"] = tex.name
                                    if k == "specularTexture":
                                        srtDraw["PRenderState"]["ApTextures"][4]["Val"] = tex.name
                                        srtDraw["PRenderState"]["ApTextures"][5]["Val"] = tex.name
                                
                            # Properties
                            prop_index = 0
                            properties = properties[1:-1]
                            for property in srtDraw["PRenderState"]["SVertexDecl"]["AsProperties"]:
                                property["AeProperties"] = [properties[prop_index], properties[prop_index+1],
                                properties[prop_index+2], properties[prop_index+3]]
                                property["AePropertyComponents"] = [components[prop_index], components[prop_index+1],
                                components[prop_index+2], components[prop_index+3]]
                                property["AuiVertexOffsets"] = [offsets[prop_index], offsets[prop_index+1],
                                offsets[prop_index+2], offsets[prop_index+3]]
                                property["EFormat"] = formats[prop_index+3]
                                prop_index += 4
                            
                            # Attributes
                            attributes_components = getAttributesComponents(attributes)
                            srtAttributes = srtDraw["PRenderState"]["SVertexDecl"]["AsAttributes"]
                            # Attrib 0
                            if "VERTEX_PROPERTY_POSITION" in properties:
                                attrib0 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_POSITION" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib0[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_POSITION" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib0[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_POSITION" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib0[2] = i
                                srtAttributes[0]["AeAttribs"] = [attributes[x] for x in attrib0]
                                srtAttributes[0]["AeAttribComponents"] = [attributes_components[x] for x in attrib0]
                                srtAttributes[0]["AuiOffsets"] = [offsets[x] for x in attrib0]
                                srtAttributes[0]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 1
                            if "VERTEX_PROPERTY_DIFFUSE_TEXCOORDS" in properties:
                                attrib1 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_DIFFUSE_TEXCOORDS" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib1[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_DIFFUSE_TEXCOORDS" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib1[1] = i
                                srtAttributes[1]["AeAttribs"] = [attributes[x] for x in attrib1]
                                srtAttributes[1]["AeAttribComponents"] = [attributes_components[x] for x in attrib1]
                                srtAttributes[1]["AuiOffsets"] = [offsets[x] for x in attrib1]
                                srtAttributes[1]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 2
                            if "VERTEX_PROPERTY_NORMAL" in properties:
                                attrib2 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_NORMAL" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib2[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_NORMAL" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib2[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_NORMAL" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib2[2] = i
                                srtAttributes[2]["AeAttribs"] = [attributes[x] for x in attrib2]
                                srtAttributes[2]["AeAttribComponents"] = [attributes_components[x] for x in attrib2]
                                srtAttributes[2]["AuiOffsets"] = [offsets[x] for x in attrib2]
                                srtAttributes[2]["EFormat"] = "VERTEX_FORMAT_BYTE"
                            # Attrib 3
                            if "VERTEX_PROPERTY_LOD_POSITION" in properties:
                                attrib3 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_LOD_POSITION" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib3[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_LOD_POSITION" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib3[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_LOD_POSITION" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib3[2] = i
                                srtAttributes[3]["AeAttribs"] = [attributes[x] for x in attrib3]
                                srtAttributes[3]["AeAttribComponents"] = [attributes_components[x] for x in attrib3]
                                srtAttributes[3]["AuiOffsets"] = [offsets[x] for x in attrib3]
                                srtAttributes[3]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 4
                            if "VERTEX_PROPERTY_GEOMETRY_TYPE_HINT" in properties:
                                attrib4 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_GEOMETRY_TYPE_HINT" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib4[0] = i
                                srtAttributes[4]["AeAttribs"] = [attributes[x] for x in attrib4]
                                srtAttributes[4]["AeAttribComponents"] = [attributes_components[x] for x in attrib4]
                                srtAttributes[4]["AuiOffsets"] = [offsets[x] for x in attrib4]
                                srtAttributes[4]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 5
                            if "VERTEX_PROPERTY_LEAF_CARD_CORNER" in properties:
                                attrib5 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_LEAF_CARD_CORNER" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib5[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_LEAF_CARD_CORNER" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib5[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_LEAF_CARD_CORNER" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib5[2] = i
                                srtAttributes[5]["AeAttribs"] = [attributes[x] for x in attrib5]
                                srtAttributes[5]["AeAttribComponents"] = [attributes_components[x] for x in attrib5]
                                srtAttributes[5]["AuiOffsets"] = [offsets[x] for x in attrib5]
                                srtAttributes[5]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 6
                            if "VERTEX_PROPERTY_LEAF_CARD_LOD_SCALAR" in properties:
                                attrib6 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_LEAF_CARD_LOD_SCALAR" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib6[0] = i
                                srtAttributes[6]["AeAttribs"] = [attributes[x] for x in attrib6]
                                srtAttributes[6]["AeAttribComponents"] = [attributes_components[x] for x in attrib6]
                                srtAttributes[6]["AuiOffsets"] = [offsets[x] for x in attrib6]
                                srtAttributes[6]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 8
                            if "VERTEX_PROPERTY_WIND_BRANCH_DATA" in properties:
                                attrib8 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_WIND_BRANCH_DATA" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib8[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_WIND_BRANCH_DATA" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib8[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_WIND_BRANCH_DATA" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib8[2] = i
                                    if properties[i] == "VERTEX_PROPERTY_WIND_BRANCH_DATA" and components[i] == "VERTEX_COMPONENT_W":
                                        attrib8[3] = i
                                srtAttributes[8]["AeAttribs"] = [attributes[x] for x in attrib8]
                                srtAttributes[8]["AeAttribComponents"] = [attributes_components[x] for x in attrib8]
                                srtAttributes[8]["AuiOffsets"] = [offsets[x] for x in attrib8]
                                srtAttributes[8]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 9
                            if "VERTEX_PROPERTY_WIND_EXTRA_DATA" in properties:
                                attrib9 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_WIND_EXTRA_DATA" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib9[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_WIND_EXTRA_DATA" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib9[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_WIND_EXTRA_DATA" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib9[2] = i
                                srtAttributes[9]["AeAttribs"] = [attributes[x] for x in attrib9]
                                srtAttributes[9]["AeAttribComponents"] = [attributes_components[x] for x in attrib9]
                                srtAttributes[9]["AuiOffsets"] = [offsets[x] for x in attrib9]
                                srtAttributes[9]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 10
                            if "VERTEX_PROPERTY_WIND_FLAGS" in properties:
                                attrib10 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_WIND_FLAGS" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib10[0] = i
                                srtAttributes[10]["AeAttribs"] = [attributes[x] for x in attrib10]
                                srtAttributes[10]["AeAttribComponents"] = [attributes_components[x] for x in attrib10]
                                srtAttributes[10]["AuiOffsets"] = [offsets[x] for x in attrib10]
                                srtAttributes[10]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 11
                            if "VERTEX_PROPERTY_LEAF_ANCHOR_POINT" in properties:
                                attrib11 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_LEAF_ANCHOR_POINT" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib11[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_LEAF_ANCHOR_POINT" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib11[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_LEAF_ANCHOR_POINT" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib11[2] = i
                                srtAttributes[11]["AeAttribs"] = [attributes[x] for x in attrib11]
                                srtAttributes[11]["AeAttribComponents"] = [attributes_components[x] for x in attrib11]
                                srtAttributes[11]["AuiOffsets"] = [offsets[x] for x in attrib11]
                                srtAttributes[11]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 13
                            if "VERTEX_PROPERTY_BRANCH_SEAM_DIFFUSE" in properties:
                                attrib13 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_BRANCH_SEAM_DIFFUSE" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib13[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_BRANCH_SEAM_DIFFUSE" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib13[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_BRANCH_SEAM_DIFFUSE" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib13[2] = i
                                srtAttributes[13]["AeAttribs"] = [attributes[x] for x in attrib13]
                                srtAttributes[13]["AeAttribComponents"] = [attributes_components[x] for x in attrib13]
                                srtAttributes[13]["AuiOffsets"] = [offsets[x] for x in attrib13]
                                srtAttributes[13]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 14
                            if "VERTEX_PROPERTY_BRANCH_SEAM_DETAIL" in properties:
                                attrib14 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_BRANCH_SEAM_DETAIL" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib14[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_BRANCH_SEAM_DETAIL" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib14[1] = i
                                srtAttributes[14]["AeAttribs"] = [attributes[x] for x in attrib14]
                                srtAttributes[14]["AeAttribComponents"] = [attributes_components[x] for x in attrib14]
                                srtAttributes[14]["AuiOffsets"] = [offsets[x] for x in attrib14]
                                srtAttributes[14]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 15
                            if "VERTEX_PROPERTY_DETAIL_TEXCOORDS" in properties:
                                attrib15 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_DETAIL_TEXCOORDS" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib15[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_DETAIL_TEXCOORDS" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib15[1] = i
                                srtAttributes[15]["AeAttribs"] = [attributes[x] for x in attrib15]
                                srtAttributes[15]["AeAttribComponents"] = [attributes_components[x] for x in attrib15]
                                srtAttributes[15]["AuiOffsets"] = [offsets[x] for x in attrib15]
                                srtAttributes[15]["EFormat"] = "VERTEX_FORMAT_HALF_FLOAT"
                            # Attrib 16
                            if "VERTEX_PROPERTY_TANGENT" in properties:
                                attrib16 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_TANGENT" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib16[0] = i
                                    if properties[i] == "VERTEX_PROPERTY_TANGENT" and components[i] == "VERTEX_COMPONENT_Y":
                                        attrib16[1] = i
                                    if properties[i] == "VERTEX_PROPERTY_TANGENT" and components[i] == "VERTEX_COMPONENT_Z":
                                        attrib16[2] = i
                                srtAttributes[16]["AeAttribs"] = [attributes[x] for x in attrib16]
                                srtAttributes[16]["AeAttribComponents"] = [attributes_components[x] for x in attrib16]
                                srtAttributes[16]["AuiOffsets"] = [offsets[x] for x in attrib16]
                                srtAttributes[16]["EFormat"] = "VERTEX_FORMAT_BYTE"
                            # Attrib 18
                            if "VERTEX_PROPERTY_AMBIENT_OCCLUSION" in properties:
                                attrib18 = [-1,-1,-1,-1]
                                for i in range(len(properties)):
                                    if properties[i] == "VERTEX_PROPERTY_AMBIENT_OCCLUSION" and components[i] == "VERTEX_COMPONENT_X":
                                        attrib18[0] = i
                                srtAttributes[18]["AeAttribs"] = [attributes[x] for x in attrib18]
                                srtAttributes[18]["AeAttribComponents"] = [attributes_components[x] for x in attrib18]
                                srtAttributes[18]["AuiOffsets"] = [offsets[x] for x in attrib18]
                                srtAttributes[18]["EFormat"] = "VERTEX_FORMAT_BYTE"
                                
                            srtLod["PDrawCalls"].append(srtDraw)
                            
                            # Write P3dRenderStateMain 
                            srtMain["Geometry"]["P3dRenderStateMain"].append(srtDraw["PRenderState"])
                            
                            # Write P3dRenderStateDepth
                            with open("templates/depthTemplate.json", 'r', encoding='utf-8') as depthfile:
                                srtDepth = json.load(depthfile)
                            srtMain["Geometry"]["P3dRenderStateDepth"].append(srtDepth)
                            
                            # Write P3dRenderStateShadow
                            srtMain["Geometry"]["P3dRenderStateShadow"].append(copy.deepcopy(srtDraw["PRenderState"]))
                            for i in range(1, len(srtMain["Geometry"]["P3dRenderStateShadow"][-1]["ApTextures"])):
                                srtMain["Geometry"]["P3dRenderStateShadow"][-1]["ApTextures"][i]["Val"] = ""
                            srtMain["Geometry"]["P3dRenderStateShadow"][-1]["ERenderPass"] = "RENDER_PASS_SHADOW_CAST"
                            srtMain["Geometry"]["P3dRenderStateShadow"][-1]["BFadeToBillboard"] = False
                            
                    #Join meshes back again  
                    JoinThem(mesh_names)
                    # Get Extent
                    if col == lod_colls[0]:
                        Extent = np.array(col.objects[0].bound_box)
                    
                    srtLod["NNumDrawCalls"] = len(mesh_names)
                    meshesNum += len(mesh_names)
                    srtMain["Geometry"]["PLods"].append(srtLod)                  
                        
        # Write Extent
        srtMain["Extents"]["m_cMin"] = list(Extent[0])
        srtMain["Extents"]["m_cMax"] = list(Extent[6])   
                
        # Write lodsNum et meshesNum
        srtMain["Geometry"]["NNum3dRenderStates"] = meshesNum
        srtMain["Geometry"]["NNumLods"] = lodsNum
        
        # Write LodProfile #LodProfile
        for k in srtMain["LodProfile"]:
            if hasattr(wm, k):
                srtMain["LodProfile"][k] = getattr(wm, k)
        if lodsNum > 0:
            srtMain["LodProfile"]["m_bLodIsPresent"] = True
            
        # User Strings
        if wm.EBillboardRandomType != 'NoBillboard':
            srtMain["PUserStrings"].append(wm.EBillboardRandomType)
        if wm.ETerrainNormals != 'TerrainNormalsOff':
            srtMain["PUserStrings"].append(wm.ETerrainNormals)
        while len(srtMain["PUserStrings"]) < 5:
            srtMain["PUserStrings"].append("")
            
        # StringTable
        srtMain["StringTable"] = [""]
        if wm.EBillboardRandomType != 'NoBillboard':
            srtMain["StringTable"].append(wm.EBillboardRandomType)
        if wm.ETerrainNormals != 'TerrainNormalsOff':
            srtMain["StringTable"].append(wm.ETerrainNormals)
        srtMain["StringTable"].append("../../../../../bin/shaders/speedtree")
        textures_names = np.array(textures_names)
        unique_textures_names = list(np.unique(textures_names))
        bb_textures_names = np.array(bb_textures_names)
        unique_bb_textures_names = list(np.unique(bb_textures_names))
        srtMain["StringTable"]+= unique_textures_names
        srtMain["StringTable"]+= unique_bb_textures_names    
        
        # Get fileName
        fileName = os.path.basename(filepath)[:-4] + "srt"
        
        # Write fileName
        srtMain["FileName"] = fileName
    
        #%% write the template with generated values
        with open(filepath, 'w', encoding = 'utf-8') as f:
            json.dump(srtMain, f, indent=2)
