#----------------------------------------------------
#Unreal Engine 4 Export Helper
#----------------------------------------------------
bl_info = \
    {
        "name" : "UE4ExportHelper",
        "author" : "Manuel Geissinger <manuel@artunchained.de>",
        "version" : (0, 5, 0),
        "blender" : (2, 80, 0),
        "location" : "View 3D > Object > UE4 Export",
        "description" : "Prepares objects for exporting to fbx for Unreal Engine 4",
        "warning" : "",
        "wiki_url" : "",
        "tracker_url" : "",
        "category" : "Object",
    }
    
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, UIList, AddonPreferences, PropertyGroup
from bl_operators.presets import AddPresetBase
import os
import mathutils
from mathutils import *
import re

bpy.types.Scene.singleOb = BoolProperty(default=False, description='Save each object into separate files (better for some cases with lightmapping and for high poly objects)')
bpy.types.Scene.createFolder = BoolProperty(default=False, description='Create folder for the separate files')
bpy.types.Scene.createLightmap = BoolProperty(default=False, description='Create lightmap UV layer')
bpy.types.Scene.lightmapSnap = BoolProperty(default=True, description='Snap Lightmap UVs to grid')
bpy.types.Scene.lightGrid = IntProperty(default=64, description='Lightmap resolution for grid, use power of 2! 4,8,16,32,64,128,256,...', min=4, max=2048)
bpy.types.Scene.lightMargin = FloatProperty(default=0.1, description='Lightmap island margin', min=0, max=1, step=0.1, precision=4)
bpy.types.Scene.applyTransform = BoolProperty(default=True, description='Apply transformation. Do not uncheck unless you know exactly what you are doing')
bpy.types.Scene.centerOb = BoolProperty(default=False, description='Centre each object before export (use for multiple assets that do not belong together)')
bpy.types.Scene.centerRel = BoolProperty(default=False, description='Centre each object relative to the active object')
bpy.types.Scene.orgToGeo = BoolProperty(default=False, description='Set each object\'s origin to it\'s center (important for objects with e.g. an array modifier)')
bpy.types.Scene.orgToBottomOffset = FloatProperty(default=0.0, description='Offset the bottom origin a bit, e.g. stick foliage into the ground. Positive values will stick into ground, negative will make the object float above the ground.', min=-1000, max=1000, step=0.1, precision=4)
bpy.types.Scene.orgToBottom = BoolProperty(default=False, description='Set each object\'s origin to it\'s center and bottom (important for e.g. foliage)')
bpy.types.Scene.unparent = BoolProperty(default=True, description='Clear parent on preparation')
bpy.types.Scene.join = BoolProperty(default=False, description='If you want to export multiple objects sharing the same UVs (materials) into one file, you should consider join them, otherwise lightmapping may not work.')
bpy.types.Scene.deleteCopy = BoolProperty(default=False, description='Delete the temp copies after exporting')
bpy.types.Scene.useObName = BoolProperty(default=False, description='Only use the objects name for filename instead of \"filename_objectname\"')
bpy.types.Scene.altLayout = BoolProperty(default=False, description='Use alternative layout for improved visibility with some themes.')
bpy.types.Scene.activateLOD = BoolProperty(default=False, description='Activate LOD export options. This REQUIRES a modified FBX-Exporter script. See documentation on CGC for instructions!')
bpy.types.Scene.peOneStepToogle = BoolProperty(default=False)
bpy.types.Scene.returnToLocal = StringProperty(default="")
bpy.types.Scene.selLayers = StringProperty(default="")
bpy.types.Scene.collisionType = EnumProperty(items = [('UBX', 'Box', 'Add static box as collision mesh. Don\'t deform in edit mode!'), ('USP', 'Sphere', 'Add static sphere as collision mesh. Don\'t deform in edit mode, don\'t scale on single axis!'), ('UCX', 'Convex shape', 'Add convex shape as collision mesh. Can be deformed in edit mode, but has to remain convex!')], name = "", default = 'UCX') 
bpy.types.Scene.orgOffsetType = EnumProperty(items = [('PERC', 'Percentage', 'Offset as percentage value of each object\'s height'), ('ABS', 'Absolute', 'Offset as absolute value in Blender units e.g. meters/cm')], name = "", default = 'ABS') 
    
class UE4Export_addPreset(AddPresetBase, bpy.types.Operator):
    """Add a new preset."""
    bl_idname = 'object.ue4_add_preset'
    bl_label = 'Add UE4 Export Helper Preset'
    bl_options = {'REGISTER', 'UNDO'}
    preset_menu = 'UE4Export_presets'
    preset_subdir = 'ue4exporthelper_presets'

    preset_defines = [
        "scene  = bpy.context.scene",
        ]

    preset_values = [
        "scene.singleOb",
        "scene.createFolder",
        "scene.createLightmap",
        "scene.lightmapSnap",
        "scene.lightGrid",
        "scene.lightMargin",
        "scene.applyTransform",
        "scene.centerOb",
        "scene.centerRel",
        "scene.orgToGeo",
        "scene.orgToBottom",
        "scene.unparent",
        "scene.join",
        "scene.deleteCopy",
        "scene.useObName",
        "scene.selLayers",
        "scene.path_settings.path",
        "scene.altLayout",
        "scene.collisionType",
        "scene.activateLOD"
        ]

class UE4Export_presets(bpy.types.Menu):
    """Presets for UE4 Export Helper"""
    bl_label = 'UE4 Export Helper Presets'
    bl_idname = 'UE4Export_presets'
    preset_subdir = 'ue4exporthelper_presets'
    preset_operator = 'script.execute_preset'

    draw = bpy.types.Menu.draw_preset
    
class UE4_CheckupFix(bpy.types.Operator):
    """Fix selected issue found in checkup"""
    bl_label = 'Fix it!'
    bl_idname = 'object.ue4checkupfix'
    
    fix = StringProperty()
    
    def execute(self, context):
        if self.fix == "SCENESCALE":
            bpy.context.scene.unit_settings.system = 'METRIC'
            bpy.context.scene.unit_settings.scale_length = 1.0

        return{ 'FINISHED'} 
    
class UE4_Checkup(bpy.types.Operator):
    """Check Blender setup and selected objects"""
    bl_label = 'Perform checkup'
    bl_idname = 'object.ue4checkup'

    def execute(self, context):
        checkMsg = ""
        
        """Check Blender Setup"""
        if bpy.context.scene.unit_settings.system != 'METRIC' or bpy.context.scene.unit_settings.scale_length != 1.0:
            checkMsg += ("Scene -> Units (Scale) should be set to \'Metric\' and \'1.0\'____WARNING____SCENESCALE::::")    
        else:    
            checkMsg += ("Scene -> Units (Scale) is setup correctly____OK::::")
        
        """Check Objects"""
        for ob in bpy.context.selected_objects:
            if ob.type == 'MESH' or ob.type == 'CURVE' or ob.type == 'FONT':           
                obErrors = 0
                
                """Check UV maps"""
                if ob.type == 'MESH':
                    if len(ob.data.uv_layers) == 0:
                        checkMsg += ("Object \'" + ob.name + "\' has no UV layer____ERROR::::")
                        obErrors += 1
                    if len(ob.data.uv_layers) > 1:
                        checkMsg += ("Object \'" + ob.name + "\' has more than 1 UV layer - lightmap UV creation won\'t work____WARNING::::")
                        obErrors += 1

                """Check for scale"""
                if ob.dimensions[0] < 0.01 or ob.dimensions[1] < 0.01 or ob.dimensions[2] < 0.01:
                    checkMsg += ("Object \'" + ob.name + "\' is smaller than 1cm in one or more dimensions____WARNING::::")
                    obErrors += 1
                if ob.dimensions[0] > 1000 or ob.dimensions[1] > 1000 or ob.dimensions[2] > 1000:      
                    checkMsg += ("Object \'" + ob.name + "\' is bigger than 1km in one or more dimensions____WARNING::::")
                    obErrors += 1
                    
                if ob.type == 'CURVE' or ob.type == 'FONT':               
                    checkMsg += ("Object \'" + ob.name + "\' is a " + ob.type + ". Consider converting it manually before export____WARNING::::")
                    obErrors += 1
                    
                if obErrors == 0:
                    checkMsg +=  ("Object \'" + ob.name + "\' succesfully passed checkup!____OK::::")               
            
        """Display Checkup"""
        bpy.ops.error.ue4message('INVOKE_DEFAULT', message = checkMsg)    
        return{ 'FINISHED'}

class UE4MessageOperator(bpy.types.Operator):
    bl_idname = "error.ue4message"
    bl_label = "Checkup"
    message = StringProperty()
 
    def execute(self, context):
        self.report({'INFO'}, self.message)
        print(self.message)
        return {'FINISHED'}
 
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=600, height=800)
 
    def draw(self, context):   
        row = self.layout.split(factor=0.96)
        col = row.column()
        subrow = col.row()
        subrow.label(text="UE4 Export Helper Checkup")
        subrow.prop(bpy.context.scene, "altLayout", text="Use alternative Layout")
        row.operator("error.xclose", icon='PANEL_CLOSE', text="")
        row = self.layout.row()
        for msg in self.message.split('::::'):
            if msg != "":
                box = self.layout.box()
                if bpy.context.scene.altLayout:
                    row = self.layout.row()
                else:
                    row = box.row()
                split = row.split(factor=.96)
                content = msg.split('____')
                split.label(text=content[0])
                if content[1] == "OK":               
                    split.label(icon='FILE_TICK')  
                if content[1] == "WARNING":
                    split.label(icon='ERROR')
                if content[1] == "ERROR":
                    split.label(icon='CANCEL')
                
                """Add fix button if available"""    
                try:
                    print(content[2])
                    if content[2] != "":
                        if bpy.context.scene.altLayout:
                            row = self.layout.row()
                        else:
                            row = box.split()
                        split = row.split(factor=.8)
                        split.separator()
                        split.operator("object.ue4checkupfix").fix=content[2]                          
                except:
                    pass    
                #print(msg, "   EOL")
                
        if bpy.context.scene.altLayout:
            box = self.layout.box()
        row = self.layout.row() 
        row.label(text="OK", icon='FILE_TICK')  
        row.label(text="WARNING", icon='ERROR')  
        row.label(text="ERROR", icon='CANCEL')  
        row = self.layout.row()   
        row.label(text="Move mouse out of this window to close it!") 
        
class XOperator(bpy.types.Operator):
    bl_idname = "error.xclose"
    bl_label = "X"
    def execute(self, context): 
        return {'FINISHED'}
    
def colGarbageCollect(collection, object=None):
    newCollection = ""
    separator = ""
    addElement = True
    for element in collection.split(','):
        colOb = bpy.data.objects.get(element)
        if colOb is not None: 
            if object is not None:
                substr = re.search(r'\_(.*)\_', colOb.name).group(1)
                if substr == object.name:    
                    addElement = True
                else:
                    addElement = False
                    
            if addElement:        
                newCollection += separator + element
                separator = ","
    return newCollection

def clearSelection():
    #unselect all collision objects
    for ob in bpy.context.selected_objects:
        if "UCX_" in ob.name or "USP_" in ob.name or "UBX_"in ob.name :
            ob.select_set(False)
            
    #check if the active object is a collision object, if so, make the parent the active object
    ob = bpy.context.view_layer.objects.active
    if ob is not None:        
        if "UCX_" in ob.name or "USP_" in ob.name or "UBX_"in ob.name :
            bpy.context.view_layer.objects.active = ob.parent
    
class AddCollisionMesh_UE4(bpy.types.Operator):
    """Add a collision mesh for UE4"""
    bl_idname = "object.addcollisionue4"
    bl_label = "Add"
    bl_options = {'UNDO'}

    def execute(self, context):  
        if bpy.context.view_layer.objects.active is not None:
            ob = bpy.context.view_layer.objects.active
            
            if bpy.context.scene.collisionType in ("UCX", "UBX", "USP") and bpy.context.scene.collisionObject != "":
                colOb = bpy.data.objects[bpy.context.scene.collisionObject]
                colTypeName = bpy.context.scene.collisionType
                if colOb.type == "MESH":
                    colOb.display_type = "WIRE"
                    colMatrix = colOb.matrix_world
                    colOb.parent = ob
                    colOb.matrix_world = colMatrix
                    colOb["isColOb"] = True
                    
                    colSocket = ""
                    try:
                        colSocket = ob["colSocket"]
                    except:
                        pass

                    ob["colSocket"] = colSocket = colGarbageCollect(colSocket, ob)    
                    if colSocket == "":
                        colOb.name = colTypeName + "_" + ob.name + "_00"
                        ob["colSocket"] = colOb.name 
                    else:
                        #Last two chars of the last element of the split list converted to int,
                        #incremented by 1, converted to string, filled with trailing 0 if necessary
                        #if there is more than 1 element. Otherwise just two zeros.
                        next = str(int(colSocket.split(',')[-1][-2:]) + 1).zfill(2) if len(colSocket.split(',')) > 0 else "00"
                        colOb.name = colTypeName + "_" + ob.name + "_" + next
                        exists=False
                        for name in colSocket.split(','):
                            if name == colOb.name:
                                exists=True
                        if not exists:
                            ob["colSocket"] += ","+colOb.name 
                        
                    bpy.context.scene.collisionObject = ""                 
        return {'FINISHED'}
    

class UE4Export_removeCollision(bpy.types.Operator):
    """Remove a collision mesh from active object."""
    bl_idname = 'object.ue4_remove_collision'
    bl_label = 'Remove a collision mesh from active object.'
    bl_options = {'REGISTER', 'UNDO'}
    
    activeName = StringProperty()
    
    def execute(self, context):
        if self.activeName != "":
            if bpy.context.view_layer.objects.active is not None:
                activeOb =  bpy.context.view_layer.objects.active    
                
                ob = bpy.data.objects[self.activeName]
                ob.name = "UE4EH removed collision mesh"
                ob.parent = None
                ob.display_type = "TEXTURED"
                ob["isColOb"] = False
                
                colSocket = ""
                try:
                    colSocket = activeOb["colSocket"]
                    colSocket = colSocket.replace(self.activeName, "")
                    colSocket = colSocket.lstrip(",")
                    colSocket = colSocket.rstrip(",")
                    colSocket = colSocket.replace(",,", ",")
                    activeOb["colSocket"] = colSocket
                except:
                    pass
        return{ 'FINISHED'} 
    
class AddLODMesh_UE4(bpy.types.Operator):
    """Add a LOD mesh for UE4"""
    bl_idname = "object.addlodue4"
    bl_label = "Add"
    bl_options = {'UNDO'}

    def execute(self, context):  
        if bpy.context.view_layer.objects.active is not None:
            ob = bpy.context.view_layer.objects.active
            
            if bpy.context.scene.LODObject != "":
                LODOb = bpy.data.objects[bpy.context.scene.LODObject]

                if LODOb.type == "MESH":
                    LODOb.show_name = True
                    LODMatrix = LODOb.matrix_world
                    LODOb.parent = ob
                    LODOb.matrix_world = LODMatrix
                    LODOb["isLODOb"] = True
                    LODOb["LODparent"] = ob.name
                    
                    LODSocket = ""
                    try:
                        LODSocket = ob["lodSocket"]
                    except:
                        pass

                    ob["lodSocket"] = LODSocket = colGarbageCollect(LODSocket, ob)    
                    if LODSocket == "":
                        LODOb.name = "LOD_" + ob.name + "_00"
                        ob["lodSocket"] = LODOb.name 
                    else:
                        #Last two chars of the last element of the split list converted to int,
                        #incremented by 1, converted to string, filled with trailing 0 if necessary
                        #if there is more than 1 element. Otherwise just two zeros.
                        next = str(int(LODSocket.split(',')[-1][-2:]) + 1).zfill(2) if len(LODSocket.split(',')) > 0 else "00"
                        LODOb.name = "LOD_" + ob.name + "_" + next
                        exists=False
                        for name in LODSocket.split(','):
                            if name == LODOb.name:
                                exists=True
                        if not exists:
                            ob["lodSocket"] += ","+LODOb.name 
                        
                    bpy.context.scene.LODObject = ""        
        return {'FINISHED'}    
    

class UE4Export_removeLOD(bpy.types.Operator):
    """Remove an LOD mesh from active object."""
    bl_idname = 'object.ue4_remove_lod'
    bl_label = 'Remove an LOD mesh from active object.'
    bl_options = {'REGISTER', 'UNDO'}
    
    activeName = StringProperty()
    
    def execute(self, context):
        if self.activeName != "":
            if bpy.context.view_layer.objects.active is not None:
                activeOb =  bpy.context.view_layer.objects.active    
                
                ob = bpy.data.objects[self.activeName]
                ob.name = "UE4EH removed LOD mesh"
                ob.parent = None
                ob.display_type = "TEXTURED"
                ob["isLODOb"] = False
                ob["LODparent"] = ""
                
                LODSocket = ""
                try:
                    LODSocket = activeOb["lodSocket"]
                    LODSocket = LODSocket.replace(self.activeName, "")
                    LODSocket = LODSocket.lstrip(",")
                    LODSocket = LODSocket.rstrip(",")
                    LODSocket = LODSocket.replace(",,", ",")
                    activeOb["lodSocket"] = LODSocket
                except:
                    pass
        return{ 'FINISHED'} 

class PrepareAndExport_UE4(bpy.types.Operator):
    """Prepare and export selected objects for UE4 in one step"""
    bl_idname = "object.prepareexportue4"
    bl_label = "Prepare & Export for UE4"
    bl_options = {'UNDO'}

    def execute(self, context):   
        layers = [layer for layer in bpy.context.scene.layers]
        bpy.context.scene.selLayers = ""   
        for i in range(0,20):
             bpy.context.scene.selLayers += str(int(layers[i]))
             if i < 19:
                bpy.context.scene.selLayers += ',' 
        
        bpy.context.scene.peOneStepToogle = True
        bpy.ops.object.prepareue4()
        bpy.ops.object.callue4export('INVOKE_DEFAULT')

        return {'FINISHED'}

class Call_UE4_Export(bpy.types.Operator):
    """Call fbx exporter"""
    bl_idname = "object.callue4export"
    bl_label = "Save"
    bl_options = {'UNDO'}
    
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):              
            
        if not len(bpy.context.selected_objects) > 0:
            return {'FINISHED'}
        else:
            self.filepath = bpy.context.scene.path_settings.path
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
    
    def execute(self, context):   
        filename = self.filepath
        file = os.path.basename(filename)
        
        colList = []       
        LODList = []   
        objects = None
        
        clearSelection()
        
        if bpy.context.scene.singleOb: # Separate Files, variable name is misleading
            if filename[-4:].lower() == ".fbx":
                filename = filename[:len(filename)-4]
            if bpy.context.scene.createFolder:
                filename += "\\"                              
                
            if bpy.context.view_layer.objects.active is None:
                bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]   
    
            ob = bpy.context.view_layer.objects.active                
            objects = bpy.context.selected_objects
               
            orgLocation = ob.location.copy()
            
            for ob in objects:
                ob.select_set(False)
                
            for ob in objects:
                ob.select_set(True)
                bpy.context.view_layer.objects.active = ob
                base = filename
                if bpy.context.scene.createFolder:
                    if not os.path.exists(base):
                        os.makedirs(base)
                   
                realName = ""
                try:
                    realName = ob["realName"]
                except:
                    realName = ob.name
                    
                if bpy.context.scene.useObName:
                    path = base + realName.replace(".", "_") + ".fbx"
                else:
                    if bpy.context.scene.createFolder:
                        base += file
                    path = base+ "_" + realName.replace(".", "_") + ".fbx"
               
                thisObLocation = Vector([0, 0, 0])
                if bpy.context.scene.centerOb:
                    if bpy.context.scene.centerRel:
                        ob.location -= orgLocation 
                        thisObLocation = ob.location.copy()                   
                    else:
                        thisObLocation = ob.location.copy()
                        ob.location = Vector([0, 0, 0])
                
                #Try and select the attached collision meshes
                colSocket = ""
                try:
                    colSocket = ob["colSocket"]
                except:
                    pass
                
                colSocket = colGarbageCollect(colSocket)
                if colSocket != "":
                    for name in colSocket.split(","):
                        bpy.data.objects[name].select_set(True)
                 
                bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')    
        
                LODPrepare(ob, thisObLocation)   
                    
                bpy.ops.export_scene.fbx(filepath=path, 
                                        check_existing=True, 
                                        filter_glob="*.fbx", 
                                        use_selection=True, 
                                        global_scale=1.0, 
                                        axis_forward='-Y', 
                                        axis_up='Z', 
                                        object_types={'EMPTY', 'LIGHT', 'MESH', 'CAMERA', 'ARMATURE'}, 
                                        use_mesh_modifiers=False, 
                                        mesh_smooth_type='FACE', 
                                        use_mesh_edges=False, 
                                        use_armature_deform_only=False, 
                                        path_mode='AUTO', 
                                        batch_mode='OFF', 
                                        use_batch_own_dir=True, 
                                        use_metadata=True,
                                        add_leaf_bones=False)
                                        
                                        
                #undo the operation for the collision objects    
                """ Has to be redone for the new LOD options 
                if colSocket != "":
                    for name in colSocket.split(","):
                        colOb = bpy.data.objects[name]
                        colMatrix = colOb.matrix_world
                        colOb.parent = ob
                        colOb.matrix_world = colMatrix
                        colOb.select_set(False)
                        colList.append(colOb) """
                        
                if bpy.context.scene.centerOb:
                    if bpy.context.scene.centerRel:
                        ob.location += orgLocation                    
                    else:
                        ob.location = thisObLocation    
                ob.select_set(False)
                              
        else: # Single file        
            """Find the originally active object"""
            activeOb = None
            for ob in bpy.context.selected_objects:
                try:
                    if ob["active"]:
                        activeOb = ob
                except: 
                    pass
             
            if activeOb is not None:
               bpy.context.view_layer.objects.active = activeOb
                              
            if bpy.context.view_layer.objects.active is None:
                bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]   

            ob = bpy.context.view_layer.objects.active                
            objects = bpy.context.selected_objects
            orgLocation = ob.location.copy()
                        
            realName = ""
            try:
                realName = ob["realName"]
            except:
                realName = ob.name
                
            if bpy.context.scene.useObName:
                if len(file) > 0:
                    filename = filename[:-len(file)]
                filename += realName.replace(".", "_") + ".fbx"          
                
            if filename[-4:].lower() != ".fbx":
               filename += ".fbx"

            if bpy.context.scene.centerOb:
                for element in objects:
                    element.location -= orgLocation
       
            #Try and select the attached collision meshes
            for element in objects:
                colSocket = ""
                try:
                    colSocket = element["colSocket"]
                except:
                    pass
                
                colSocket = colGarbageCollect(colSocket)
                if colSocket != "":
                    for name in colSocket.split(","):
                        bpy.data.objects[name].select_set(True)
             
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')    

            LODPrepare(ob, orgLocation)   
    
            bpy.ops.export_scene.fbx(filepath=filename, 
                                    check_existing=True, 
                                    filter_glob="*.fbx", 
                                    use_selection=True, 
                                    global_scale=1.0, 
                                    axis_forward='Y', 
                                    axis_up='Z', 
                                    object_types={'EMPTY', 'LAMP', 'MESH', 'CAMERA', 'ARMATURE'}, 
                                    use_mesh_modifiers=False, 
                                    mesh_smooth_type='FACE', 
                                    use_mesh_edges=False, 
                                    use_armature_deform_only=False, 
                                    use_anim=True, 
                                    use_anim_action_all=True, 
                                    use_default_take=True, 
                                    use_anim_optimize=True, 
                                    anim_optimize_precision=6.0, 
                                    path_mode='AUTO', 
                                    batch_mode='OFF', 
                                    use_batch_own_dir=True, 
                                    use_metadata=True,
                                    add_leaf_bones=False)
                         
            #undo the operation for the collision objects  
            """ Has to be redone for the new LOD options
            for element in objects:
                colSocket = ""
                try:
                    colSocket = element["colSocket"]
                except:
                    pass
                
                if colSocket != "":
                    for name in colSocket.split(","):
                        colOb = bpy.data.objects[name]
                        colMatrix = colOb.matrix_world
                        colOb.parent = ob
                        colOb.matrix_world = colMatrix
                        colOb.select_set(False)
                        colList.append(colOb)     """            
            
            if bpy.context.scene.centerOb:
                for ob in objects:
                    ob.location += orgLocation          

        if bpy.context.scene.deleteCopy:                    
            for ob in objects:
                ob.select_set(True)
                
            for ob in colList:
                ob.select_set(True)
                print("colList Entry", ob.name)
                
            for ob in bpy.context.selected_objects:
                isUEEHCopy = False
                isColCopy = False
                isLODParent = False
                
                try:
                    isUEEHCopy = ob["isUEEHCopy"]
                except:
                    pass
                
                try:
                    isColCopy = ob["isColCopy"]
                except:
                    pass
                
                try:
                    isLODParent = ob["isLODParent"]
                except:
                    pass

                if not (isUEEHCopy or isColCopy or isLODParent):
                    ob.select_set(False)
            bpy.ops.object.delete(use_global=False)   
            
            if bpy.context.scene.selLayers != "":
                try:
                    bpy.context.scene.layers = tuple([bool(int(x)) for x in bpy.context.scene.selLayers.split(",")])
                except:
                    pass
                       
            if bpy.context.scene.peOneStepToogle:
                returnToLocalView()     
                bpy.context.scene.peOneStepToogle = False  
        return {'FINISHED'}
    
def exitLocalView():
    """Test for active User Local View and work around it"""
    """Local view is hardly exposed to Python so some tricks are neccesary"""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            if area.spaces.active.local_view is not None:
                bpy.context.scene.returnToLocal = ""
                
                selectedObs = bpy.context.selected_objects.copy()                            
                bpy.ops.object.select_all(action='SELECT')
                for ob in bpy.context.selected_objects:
                    bpy.context.scene.returnToLocal += ob.name + ",,,"     
                
                bpy.ops.view3d.localview()
                
                #Exiting Local View selects all objects that where in Local View before.. not what we want, we want only the objects that the user actually selected
                for ob in bpy.context.selected_objects:
                    if ob not in selectedObs:
                        ob.select_set(False)  
                        print("Found 1") 
                
                
def returnToLocalView():
    """Check if User Local View was exited before"""
    if bpy.context.scene.returnToLocal != "":
        obNames = bpy.context.scene.returnToLocal.split(",,,") 
        for obname in obNames:
            try:
                bpy.data.objects[obname].select_set(True)
            except:
                pass
        try:
            bpy.ops.view3d.localview()
        except:
            pass
            #maybe display message that local view couldn't be re-entered.
        bpy.context.scene.returnToLocal = ""    

def LODPrepare(ob, orgLocation):
    """Prepare LOD Export"""
    LODSocket = ""
    try:
        LODSocket = ob["lodSocket"]
    except:
        pass
  
    LODSocket = colGarbageCollect(LODSocket) 
                          
    if LODSocket != "":
        realName = ""
        try:
            realName = ob["realName"]
        except:
            realName = ob.name
        
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        LODParent = bpy.context.active_object
        LODParent.name = "LOD_" + realName
        LODParent.location = ob.location
        LODParent.select_set(True)
        LODParent["isLODParent"] = True
        bpy.context.scene.update()
        matrixWorld = ob.matrix_world
        print(ob.location)
        ob.parent = LODParent
        ob.matrix_world = matrixWorld
        print(ob.location)
        ob.name = mainObName = realName + "_LOD0"
        ob.select_set(True)

        LODCounter = 1
        for name in LODSocket.split(','):
            element = bpy.data.objects[name]  
            element.name = realName + "_LOD" + str(LODCounter)
            element.location -= orgLocation
            bpy.context.scene.update()
            matrixWorld = element.matrix_world
            element.parent = LODParent
            element.matrix_world = matrixWorld
            element.select_set(True)
            LODCounter += 1
        
        """Rename Collision meshes"""
        colSocket = ""
        try:
            colSocket = ob["colSocket"]
        except:
            pass
      
        colSocket = colGarbageCollect(colSocket) 
                              
        if colSocket != "":
             colCounter = 0
             for name in colSocket.split(','):
                 element = bpy.data.objects[name]
                 element.name = element.name[:4] + mainObName + "_" + str(colCounter).zfill(2)
                 colCounter += 1
                 element.select_set(True)
        
        return mainObName
        
    return "noLOD"

class Prepare_UE4_Export(bpy.types.Operator):
    """Prepare selected objects for UE4 export"""
    bl_idname = "object.prepareue4"
    bl_label = "Prepare for UE4"
    bl_options = {'UNDO'}

    def execute(self, context):                  
        if not len(bpy.context.selected_objects) > 0:
            return {'FINISHED'}
        else:
            exitLocalView()            
            clearSelection()
            scene = bpy.context.scene.collection
            if bpy.context.view_layer.objects.active is None:    
                activeOb = bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]   
                #print("UE4EH: No active object selected - result may be unexpected.")                   
            else:
                activeOb = bpy.context.view_layer.objects.active
                print("Active object is ", activeOb.name)
                
            """Select LOD Objects"""
            objects = bpy.context.selected_objects    
            for parent in objects:
                LODSocket = ""
                try:
                    LODSocket = parent["lodSocket"]
                except:
                    pass

                LODSocket = colGarbageCollect(LODSocket) 
               
                if LODSocket != "":
                    for name in LODSocket.split(','):
                        ob = bpy.data.objects[name]  
                        ob.select_set(True)  
                                      
            objects = bpy.context.selected_objects                                
            
            #bpy.context.scene.layers = (False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True)
            
            for ob in objects:
                ob.select_set(False)
                ob["active"] = False                
            activeOb["active"] = True                
            
            dupliList = []     
            LODList = {}
                
            """Create grid image"""
            if bpy.context.scene.lightmapSnap:
                #check if existing:
                imgName = "lightmap_"+str(bpy.context.scene.lightGrid)
                tempImg = None
                try:
                    tempImg =  bpy.data.images[imgName]
                except:
                    pass
                if tempImg == None:                                  
                    tempImg = bpy.ops.image.new(name=imgName, width=bpy.context.scene.lightGrid, height=bpy.context.scene.lightGrid, color=(0.0, 0.0, 0.0, 1.0), alpha=False, float=False)    
                      
            for ob in objects:                
                if ob.type == 'MESH' or ob.type == 'CURVE' or ob.type == 'FONT':                          
                    isLODOb = False
                    try:
                        isLODOb = ob["isLODOb"]
                    except:
                        isLODOb = False
                         
                    duplicate = ob.copy()         
                    duplicate.data = ob.data.copy() 
                    duplicate["realName"] = ob.name
                    duplicate["isUEEHCopy"] = True
                    scene.objects.link(duplicate)
                    #scene.update()
                    
                    if isLODOb:
                        LODList[ob.name] = duplicate.name
                        
                    if ob == activeOb:                        
                        activeOb = duplicate
                        
                    bpy.context.view_layer.objects.active = duplicate
                    #duplicate.layers = (False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True)
                    duplicate.select_set(True)
                    
                    if ob.type == 'CURVE' or ob.type == 'FONT':
                        bpy.ops.object.convert(target='MESH')
                        duplicate.select_set(True)

                    for mod in duplicate.modifiers:
                        if mod.show_viewport == True:
                            try:
                                bpy.ops.object.modifier_apply(modifier=mod.name)
                            except:
                                print("Warning: Couldn't apply modifier ", mod.name)
                        else:
                            duplicate.modifiers.remove(mod)

                    bpy.context.view_layer.objects.active = duplicate
                    
                    if bpy.context.scene.applyTransform:
                        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                        
                    if bpy.context.scene.unparent:
                        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

                    
                    if bpy.context.scene.orgToGeo or bpy.context.scene.orgToBottom:
                        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

                    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                    sel_mode = context.tool_settings.mesh_select_mode
                    context.tool_settings.mesh_select_mode = [True, False, False]
                    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                    
                    originOffset = 0
                    if bpy.context.scene.orgOffsetType == 'ABS':
                        originOffset = bpy.context.scene.orgToBottomOffset
                    if bpy.context.scene.orgOffsetType == 'PERC':
                        originOffset = duplicate.dimensions[2] / 100 * bpy.context.scene.orgToBottomOffset if bpy.context.scene.orgToBottomOffset is not 0 else 0
                        
                    for vert in duplicate.data.vertices:
                        vert.select_set(True)
                        
                        if bpy.context.scene.orgToBottom:
                            vert.co[2] += duplicate.dimensions[2] / 2 - originOffset
                    
                    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                    
                    if bpy.context.scene.createLightmap and not bpy.context.scene.join:
                        bpy.ops.mesh.uv_texture_add() 
                        #optional for objects with only 1 uv layer
                        #bpy.context.object.data.active_index = 1
                        bpy.ops.uv.select_all(action='SELECT')
                        bpy.ops.uv.pack_islands(margin=bpy.context.scene.lightMargin, rotate=True)
                        if bpy.context.scene.lightmapSnap:
                            orgImage = None
                    
                            area_type = bpy.context.area.type
                            bpy.context.area.type = 'IMAGE_EDITOR'
                            orgImage =  bpy.context.space_data.image 
                            bpy.context.space_data.image = bpy.data.images[imgName]

                            bpy.ops.uv.snap_selected(target='PIXELS')
                            if orgImage != None:
                                bpy.context.area.spaces.active.image = orgImage
                            bpy.context.area.type = area_type    
                   
                    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
                        
                    context.tool_settings.mesh_select_mode = sel_mode
                    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)                   
                    
                    if bpy.context.scene.orgToBottom:
                        duplicate.location[2] -= duplicate.dimensions[2] / 2 - originOffset
                    duplicate.select_set(False)
                    
                    dupliList.append(duplicate)
                    
 
            #hidden objects get exported by the fbx exporter and so lead to mindbugging errors
            bpy.ops.object.hide_view_clear()
            
            for ob in dupliList:
                isLODOb = False
                try:
                    isLODOb = ob["isLODOb"]
                except: 
                    pass
                if not isLODOb:
                    ob.select_set(True)
                            
            if bpy.context.scene.join:
                activeOb.select_set(True)
                bpy.context.view_layer.objects.active = activeOb
                bpy.ops.object.join()
                
            """When objects are joined, lightmap needs to be created after joining"""

            if bpy.context.scene.createLightmap and bpy.context.scene.join:
                bpy.context.view_layer.objects.active.select_set(True)
                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                sel_mode = context.tool_settings.mesh_select_mode
                context.tool_settings.mesh_select_mode = [True, False, False]
                bpy.ops.object.mode_set(mode='OBJECT', toggle   =False)

                for vert in activeOb.data.vertices:
                    vert.select_set(True)
                    
                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            
                bpy.ops.mesh.uv_texture_add() 
                bpy.ops.uv.select_all(action='SELECT')
                bpy.ops.uv.pack_islands(margin=bpy.context.scene.lightMargin, rotate=True)
                if bpy.context.scene.lightmapSnap:
                    orgImage = None
            
                    area_type = bpy.context.area.type
                    bpy.context.area.type = 'IMAGE_EDITOR'
                    orgImage =  bpy.context.space_data.image 
                    bpy.context.space_data.image = bpy.data.images[imgName]

                    bpy.ops.uv.snap_selected(target='PIXELS')
                    if orgImage != None:
                        bpy.context.area.spaces.active.image = orgImage
                    bpy.context.area.type = area_type

                context.tool_settings.mesh_select_mode = sel_mode
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                
            #find attached collision meshes and copy them, too
            #Also redo the list of LOD objects
            #the naming also needs to be remade, as Blender force-renames the copies
            lastActiveParent = None
            for parent in dupliList:
                lastActiveParent = parent

                colSocket = ""
                try:
                    colSocket = parent["colSocket"]
                except:
                    pass
                
                LODSocket = ""
                try:
                    LODSocket = parent["lodSocket"]
                except:
                    pass

                colSocket = colGarbageCollect(colSocket) 
                LODSocket = colGarbageCollect(LODSocket) 

                if LODSocket != "":
                    parent["lodSocket"] = ""
                    separator = ""
                    for name in LODSocket.split(','):
                        parent["lodSocket"] += separator + LODList[name] 
                        separator = ","
                
      
                if colSocket != "":
                    colIndex = 0
                    separator = ""
                    newColSocket = ""
                    for name in colSocket.split(','):
                        #print("name", name)
                        ob = bpy.data.objects[name]
                        duplicate = ob.copy()         
                        duplicate.data = ob.data.copy() 
                        duplicate["realName"] = ob.name
                        duplicate["isColCopy"] = True
                        scene.objects.link(duplicate)
                        #scene.update()
                        
                        bpy.context.view_layer.objects.active = duplicate
                        #duplicate.layers = (False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True)
                        duplicate.select_set(True)

                        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                        dupMatrix = duplicate.matrix_world
                        duplicate.parent = parent
                        duplicate.matrix_world = dupMatrix
                        
                        if "UCX_" in duplicate.name or "USP_" in duplicate.name or "UBX_"in duplicate.name:
                            colTypeName = ""
                            if "UCX_" in duplicate.name:
                                colTypeName = "UCX"
                            if "USP_" in duplicate.name:
                                colTypeName = "USP"
                            if "UBX_" in duplicate.name:
                                colTypeName = "UBX"
                            duplicate.name = colTypeName + "_" + parent.name + "_" + str(colIndex).zfill(2)
                            newColSocket += separator + duplicate.name
                            colIndex += 1
                            if colIndex > 0:
                                separator = ","
                                
                        duplicate.select_set(False)
                        
                    parent["colSocket"] = newColSocket
                    #print("newColSocket", newColSocket)
            
            if lastActiveParent is not None:
                bpy.context.view_layer.objects.active = lastActiveParent
            
            """Return to Local View only if no export happens after. Otherwise the exporter function takes care of Local View"""
            if not bpy.context.scene.peOneStepToogle:
                returnToLocalView()                 
            
            return {'FINISHED'}
        
class PathSettings(PropertyGroup):
    path: StringProperty(
        name="",
        description="Path to Directory",
        default="",
        maxlen=1024,
        subtype='DIR_PATH')

class UE4PreparePanel(bpy.types.Panel):
    """UE4 Export Helper"""
    bl_label = "UE4 Export Helper"
    bl_idname = "OBJECT_PT_ueprep"
    bl_space_type = "VIEW_3D"    
    bl_region_type = "TOOLS"  
    #bl_category = 'UE4EH'
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        
        col = layout.column_flow(align=True)
        col.label(text='UE4 Export Helper Presets')
        row = col.row(align=True)
        row.menu("UE4Export_presets",
                 text=bpy.types.UE4Export_presets.bl_label)
        row.operator("object.ue4_add_preset", text="Add Preset")
        row.operator("object.ue4_add_preset", text="Remove Preset").remove_active = True
        
        col = layout.column(align=True)
        row = col.row(align=True)
        split = row.split(align=True)
        split.operator("object.prepareue4")
        split.operator("object.callue4export", text="Export FBX for UE4")
        row = col.row(align=True)
        row.operator("object.prepareexportue4", text="Prepare & Export in one step")
        row = layout.row()
        row.operator("object.ue4checkup")

        """General Options"""
        row = layout.row(align=True)
        row.label(text='General Options')
        
        col = layout.column_flow(align=True)
        col.label(text='UE4 Collision Meshes')
        row = col.row(align=True)
        row.operator("object.addcollisionue4", text="Add")
        row.prop(context.scene, "collisionType")    
        
        ##################### Remaining GUI Error ##################################
        if bpy.context.scene.collisionType in ("UCX", "UBX", "USP"):
            row = col.row(align=True)
            row.prop_search(context.scene, "collisionObject", context.scene, "objects", text="")
             
        if bpy.context.view_layer.objects.active is not None:   
            colMeshes = ""
            try:
                colMeshes = bpy.context.view_layer.objects.active["colSocket"] 
            except:
                pass
            if colMeshes != "":
                row = col.row(align=True)
                row.label(text="Attached collision mesh(es):")
                for name in colMeshes.split(','):
                    row = col.row(align=True)
                    row.label(text=name)         
                    row.operator("object.ue4_remove_collision", text="", icon='ZOOM_OUT').activeName=name
        
        if bpy.context.view_layer.objects.active is not None:
            ob = bpy.context.view_layer.objects.active
            cMeshes = ""
            try:
                cMeshes = ob["cMeshes"]
            except:
                pass
            if cMeshes != "":
                for lb in cMeshes.split(","):
                    if bpy.data.objects.get(lb) is not None:
                        row = col.row(align=True)
                        row.label(text=lb)    
        ##################### Remaining GUI Error ##################################                
                               
        """LOD Activation and options"""
        split = layout.split(align=True)
        col = split.column(align=True)
        col.prop(context.scene, "activateLOD", text="Activate LOD Export")
        
        if context.scene.activateLOD:
            col = layout.column_flow(align=True)
            col.label(text='UE4 LOD Meshes')
            row = col.row(align=True)
            row.operator("object.addlodue4", text="Add")
            row.prop_search(context.scene, "LODObject", context.scene, "objects", text="")
                 
            if bpy.context.view_layer.objects.active is not None:   
                lodMeshes = ""
                try:
                    lodMeshes = bpy.context.view_layer.objects.active["lodSocket"] 
                except:
                    pass
                if lodMeshes != "":
                    row = col.row(align=True)
                    row.label(text="Attached LOD mesh(es):")
                    for name in lodMeshes.split(','):
                        row = col.row(align=True)
                        row.label(text=name)         
                        row.operator("object.ue4_remove_lod", text="", icon='ZOOMOUT').activeName=name
        
        """Preparation Options"""
        split = layout.split(align=True)  
        split.label(text="Preparation Options")
      
        split = layout.split(align=True)
        col = split.column(align=True)
        col.prop(context.scene, "createLightmap", text="Create Lightmap UV Layer")
        col = split.column(align=True)
        col.prop(context.scene, "applyTransform", text="Apply Transformation")
        if context.scene.createLightmap:
             split = layout.split(align=True)
             col = split.column(align=True)
             col.prop(context.scene, "lightmapSnap", text="Snap UVs to grid")
             col = split.column(align=True)
             col.prop(context.scene, "lightGrid", text="Lightmap Resolution")
             col.prop(context.scene, "lightMargin", text="Island Margin")
             
        split = layout.split(align=True)
        col = split.column(align=True)
        col.prop(context.scene, "unparent", text="Clear Parent")
        col = split.column(align=True)
        col.prop(context.scene, "join", text="Join Objects")
        split = layout.split(align=True)
        col = split.column(align=True)
        col.prop(context.scene, "orgToGeo", text="Origin To Geometry")
        col = split.column(align=True)
        col.prop(context.scene, "orgToBottom", text="Origin To Bottom of Geometry")
        if context.scene.orgToBottom:
            split = layout.split(align=True, percentage=0.25)
            col = split.column(align=True)
            col.prop(context.scene, "orgOffsetType")
            col = split.column(align=True)
            col.prop(context.scene, "orgToBottomOffset", text="Offset bottom origin")

        
        """Export options"""
        split = layout.split(align=True)
        split.label(text="Export Options")
        split = layout.split(align=True)

        col = split.column(align=True)
        col.prop(context.scene, "singleOb", text="Separate Files")
        if context.scene.singleOb:
            col = split.column(align=True)
            col.prop(context.scene, "createFolder", text="Create Folder")
        
        split = layout.split(align=True)
        col = split.column(align=True)
        col.prop(context.scene, "useObName", text="Only objects\' name")   
         
        split = layout.split(align=True)
        col = split.column(align=True)
        col.prop(context.scene, "centerOb", text="Centre objects")
        if context.scene.centerOb:
            col = split.column(align=True)
            col.prop(context.scene, "centerRel", text="Centre relative")
            
        split = layout.split(align=True)
        col = split.column(align=True)
        col.prop(context.scene, "deleteCopy", text="Delete copies"),
        split = layout.split()
        col = split.column()
        col.label(text="Default Path")
        col.prop(context.scene.path_settings, "path", text="")
 
classes = (
    UE4Export_addPreset,
    UE4Export_presets,
    UE4_CheckupFix,
    UE4_Checkup,
    UE4MessageOperator,
    XOperator,
    AddCollisionMesh_UE4,
    UE4Export_removeCollision,
    AddLODMesh_UE4,
	UE4Export_removeLOD,
	PrepareAndExport_UE4,
	Call_UE4_Export,
	Prepare_UE4_Export,
	PathSettings,
	UE4PreparePanel
)        
 
def register():
    ####bpy.utils.register_module(__name__)
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.path_settings = PointerProperty(type=PathSettings)
    bpy.types.Scene.collisionObject = bpy.props.StringProperty()
    bpy.types.Scene.LODObject = bpy.props.StringProperty()


def unregister():
    ####bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.path_settings
    del bpy.types.Scene.collisionObject
    del bpy.types.Scene.LODObject
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
if __name__ == "__main__":
    register()
