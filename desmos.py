# SPDX-License-Identifier: GPL-2.0-or-later
bl_info = {
    "name": "Desmos Expressions",
    "author": "Ezra Oppenheimer (Heavenira)",
    "version": (1, 0, 0),
    "blender": (3, 3, 0),
    "location": "File > Import/Export",
    "description": "Export Desmos mesh data so that objects can be pasted into the graphing calculator",
    "doc_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export",
}

# Copyright (C) 2023: Ezra Oppenheimer, ezra.oppenheimer@gmail.com

import bpy, bmesh, math, json, os, time

from bpy.props import (
    EnumProperty,
    StringProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
)
from bpy_extras.io_utils import (
    ExportHelper
)


class ExportDESMOS(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.desmos"
    bl_label = "Export to Desmos"
    bl_description = "Export as Desmos expressions including pastable normals, materials and animations"

    filename_ext = ".txt"
    filter_glob: StringProperty(default="*.txt", options={'HIDDEN'})
    
    type_output: EnumProperty(
        name="Output Format",
        description="Choose which procedure to insert into Desmos",
        items=(
            ("TXT", "Desmos Expressions (.txt)", "Inject the LaTeX equations per each expression"),
            ("JSON", "Desmos JSON (.json)", "Inject via JavaScript using only Calc.setState()"),
        ),
        default="TXT",
    )
    
    # Naming Settings
    use_names: BoolProperty(
        name="Object Names",
        description="Variables will include the names for each of the objects. Else use a generic number at the end",
        default=False,
    )
    
    use_full_precision: BoolProperty(
        name="Use Full-Precision",
        description="Avoid rounding (WARNING: Results will become very large)",
        default=False,
    )
    
    
    # Geometry Settings
    use_vertices: BoolProperty(
        name="Vertices",
        description="Export mesh vertices",
        default=True,
    )
    use_faces: BoolProperty(
        name="Vertex Indices",
        description="Export vertex indices",
        default=True,
    )
    use_midpoints: BoolProperty(
        name="Midpoints",
        description="Export face midpoints (requires Faces)",
        default=False,
    )
    use_normals: BoolProperty(
        name="Normals",
        description="Export face normals (requires Faces)",
        default=False,
    )
    attach_normals: BoolProperty(
        name="Attach Normals",
        description="Shrink the normals and attach them to the midpoints (N * 0.01 + M)",
        default=False,
    )
    use_materials: BoolProperty(
        name="Materials",
        description="Export face material indices (requires Faces)",
        default=False,
    )
    triangulate_mesh: BoolProperty(
        name="Triangulate Mesh",
        description="Convert the mesh to triangles in the export",
        default=False,
    )
    use_geo_x: BoolProperty(
        name="X Geometry",
        description="Export X geometry",
        default=True,
    )
    use_geo_y: BoolProperty(
        name="Y Geometry",
        description="Export Y geometry",
        default=True,
    )
    use_geo_z: BoolProperty(
        name="Z Geometry",
        description="Export Z geometry",
        default=True,
    )
    
    
    
    # Animation Settings
    use_animation: BoolProperty(
        name="Use Animation",
        description="Export the keyframes of each object",
        default=False,
    )
    
    frame_start: IntProperty(
        name="Start Frame",
        description="The first frame to be exported",
        soft_min=0,
        default=1
    )
    frame_end: IntProperty(
        name="End Frame",
        description="The last frame to be exported",
        soft_min=0,
        default=100
    )
    frame_step: IntProperty(
        name="Frame Step",
        description="The number of frames to skip forward",
        min=1,
        soft_max=500,
        default=1
    )
    
    # Locations
    use_location_x: BoolProperty(
        name="X Location",
        description="Export X location keyframes",
        default=True,
    )
    use_location_y: BoolProperty(
        name="Y Location",
        description="Export Y location keyframes",
        default=True,
    )
    use_location_z: BoolProperty(
        name="Z Location",
        description="Export Z location keyframes",
        default=True,
    )
    use_location_global: BoolProperty(
        name="Global Location",
        description="Calculate the final XYZ positions and return those values. Else use raw channels",
        default=False,
    )
    
    # Rotations
    use_rotation_x: BoolProperty(
        name="X Rotation",
        description="Export X rotation keyframes",
        default=True,
    )
    use_rotation_y: BoolProperty(
        name="Y Rotation",
        description="Export Y rotation keyframes",
        default=True,
    )
    use_rotation_z: BoolProperty(
        name="Z Rotation",
        description="Export Z rotation keyframes",
        default=True,
    )
    use_rotation_global: BoolProperty(
        name="Global Rotation",
        description="Calculate the final euler rotations and return those values. Else use raw channels",
        default=False,
    )
    type_rotation_euler: EnumProperty(
        name="Euler Rotation",
        description="Order in which the rotation matrix transform should be calculated",
        items=(
            ("ZYX", "Euler (ZYX)", "Convert rotations to euler ZYX"),
            ("ZXY", "Euler (ZXY)", "Convert rotations to euler ZXY"),
            ("YZX", "Euler (YZX)", "Convert rotations to euler YZX"),
            ("YXZ", "Euler (YXZ)", "Convert rotations to euler YXZ"),
            ("XZY", "Euler (XZY)", "Convert rotations to euler XZY"),
            ("XYZ", "Euler (XYZ)", "Convert rotations to euler XYZ"),
        ),
        default="XYZ",
    )
    type_rotation_units: EnumProperty(
        name="Rotation Unit",
        description="Units to output the rotations in",
        items=(
            ("RAD", "Radians", "Output rotations as radians"),
            ("DEG", "Degrees", "Output rotations as degrees"),
        ),
        default="RAD",
    )
    
    # Scales
    use_scale_x: BoolProperty(
        name="X Scale",
        description="Export X scale keyframes",
        default=False,
    )
    use_scale_y: BoolProperty(
        name="Y Scale",
        description="Export Y scale keyframes",
        default=False,
    )
    use_scale_z: BoolProperty(
        name="Z Scale",
        description="Export Z scale keyframes",
        default=False,
    )
    use_scale_global: BoolProperty(
        name="Global Scale",
        description="Calculate the final XYZ scales and return those values. Else use raw channels",
        default=False,
    )
    
    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        return True
        return len(bpy.context.selected_objects) > 0
    
    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator
        
        layout.prop(operator, "type_output", text="Output")
        layout.use_property_split = True
        
        # Format Settings
        format_box = layout.box()
        format_box.label(text="Naming", icon="TEXT")
        format_box.prop(operator, "use_names")
        format_box.prop(operator, "use_full_precision", text="Use Full-Precision")
        
        # Geometry Settings
        geo_box = layout.box()
        geo_box.label(text="Geometry", icon="EXPORT")
        
        bools = geo_box.column(align=True, heading="Export")
        bools.prop(operator, "use_vertices", text="Vertices")
        if_vertices = bools.column()
        if_vertices.enabled = operator.use_vertices
        if_vertices.prop(operator, "use_faces", text="Faces")
        if_faces = if_vertices.column(align=True)
        if_faces.enabled = operator.use_faces
        if_faces.prop(operator, "use_midpoints", text="Midpoints")
        if_faces.prop(operator, "use_normals", text="Normals")
        if operator.use_midpoints and operator.use_normals:
            if_faces.prop(operator, "attach_normals", text="Attach Normals", toggle=True)
        else:
            operator.attach_normals = False
        if_faces.prop(operator, "use_materials", text="Materials")
        
        row = if_vertices.row(heading="Include")
        row.prop(operator, "use_geo_x", text="X")
        row.prop(operator, "use_geo_y", text="Y")
        row.prop(operator, "use_geo_z", text="Z")
        
        if_faces = if_vertices.column(align=True)
        if_faces.enabled = operator.use_faces
        if_faces.prop(operator, "triangulate_mesh", text="Triangulate Mesh", toggle=True)
        
        # Animation Settings
        anim_box = layout.box()
        anim_box.label(text="Animation", icon="ANIM_DATA")
        anim_box.prop(operator, "use_animation", text="Use Animation")
        
        frames = anim_box.column(align=True)
        frames.enabled = operator.use_animation
        frames.prop(operator, "frame_start", text="Frame Start")
        frames.prop(operator, "frame_end", text="End")
        frames.prop(operator, "frame_step", text="Step")
        if operator.frame_start > operator.frame_end:
            operator.frame_end = operator.frame_start
        
        if operator.use_animation:
            channels = anim_box.column(align=True)
            #channels.enabled = operator.use_animation
            
            row = channels.row(heading="Location")
            row.prop(operator, "use_location_x", text="X")
            row.prop(operator, "use_location_y", text="Y")
            row.prop(operator, "use_location_z", text="Z")
            
            row = channels.row(heading="Rotation")
            row.prop(operator, "use_rotation_x", text="X")
            row.prop(operator, "use_rotation_y", text="Y")
            row.prop(operator, "use_rotation_z", text="Z")
            
            row = channels.row(heading="Scale")
            row.prop(operator, "use_scale_x", text="X")
            row.prop(operator, "use_scale_y", text="Y")
            row.prop(operator, "use_scale_z", text="Z")
            
            transformations = anim_box.column(heading="Use Global", align=True)
            row = transformations.row(align=True)
            row.enabled = operator.use_location_x or operator.use_location_y or operator.use_location_z
            row.prop(operator, "use_location_global", text="Position")
            row = transformations.row(align=True)
            row.enabled = operator.use_rotation_x or operator.use_rotation_y or operator.use_rotation_z
            row.prop(operator, "use_rotation_global", text="Rotation")
            row = transformations.row(align=True)
            row.enabled = operator.use_scale_x or operator.use_scale_y or operator.use_scale_z
            row.prop(operator, "use_scale_global", text="Scale")
            
            if_rot = anim_box.column(align=True)
            if_rot.enabled = operator.use_rotation_x or operator.use_rotation_y or operator.use_rotation_z
            if_rot.prop(operator, "type_rotation_units", text="Unit")
            if operator.use_rotation_global:
                if_rot.prop(operator, "type_rotation_euler", text="Euler")
        
            anim_box.label(text="(Blender uses Z-Up. No other options here.)")
        pass
    
    # run this when the user clicks Export
    def execute(self, context):
        filepath = self.filepath
        
        export = export_desmos(self, context)
        
        file_contents = export[0]
        output_code = export[1]
        
        if output_code == 1:
            self.report({"WARNING"}, "Detected a face with more than 4 vertices. You might want to enable \"Triangulate Mesh\" in the future.")
        
        if self.type_output == "JSON":
            filename = os.path.basename(filepath)
            current_timestamp = time.time()
            current_time_string = time.ctime(current_timestamp).replace("  ", " ")
            file_contents = file_contents.replace('"title": "Blender Import"', f'"title": "`{filename}`\\n({current_time_string})"')
        
        fh = open(filepath, "w")
        fh.write(file_contents)
        fh.close()
        
        return {'FINISHED'}




def export_desmos(op, context):
    # This is the final dictionary. As I add objects, I will push the information to this.
    final = {}
    is_face_too_large = False
    object_count = 1
    
    
    for selected_object in context.selected_objects:
        final[selected_object.name] = {}
        obj = final[selected_object.name]
        
        # Geometry Export
        
        data = selected_object.data
        
        # let's check if we need to triangulate the mesh beforehand
        if op.triangulate_mesh:
            # Create a temporary data that alters the mesh safely
            temp_data = selected_object.data.copy()
            # Get the active mesh object
            mesh = temp_data
            
            # Create a BMesh object from the mesh data
            bm = bmesh.new()
            bm.from_mesh(mesh)

            # Triangulate the mesh
            bmesh.ops.triangulate(bm, faces=bm.faces)

            # Update the mesh data with the modified BMesh object
            bm.to_mesh(mesh)

            # Free the BMesh object
            bm.free()
            
            # now this is our new pointer
            data = mesh
        
        
        # Vertices

        # if vertices are enabled, we are good to export the geometry
        if op.use_vertices:
            if op.use_geo_x or op.use_geo_y or op.use_geo_z:
                obj["vert"] = {}
                vert = obj["vert"]
            if op.use_geo_x:
                vert["x"] = []
            if op.use_geo_y:
                vert["y"] = []
            if op.use_geo_z:
                vert["z"] = []
            for vert_element in data.vertices.values():
                if op.use_geo_x:
                    vert["x"].append(vert_element.co.x)
                if op.use_geo_y:
                    vert["y"].append(vert_element.co.y)
                if op.use_geo_z:
                    vert["z"].append(vert_element.co.z)
            
            # Faces
            if op.use_faces:
                obj["face"] = {}
                face = obj["face"]

                # we can get the largest face dimension beforehand here
                largest_dimension = 0
                for polygon_element in data.polygons.values():
                    if largest_dimension < len(polygon_element.vertices):
                        largest_dimension = len(polygon_element.vertices)
                if largest_dimension > 4:
                    is_face_too_large = True
                
                for polygon_element in data.polygons.values():
                    i = 0
                    for vert_index in polygon_element.vertices:
                        try:
                            face[f"{i+1:0>2d}"].append(vert_index + 1)
                        except:
                            face[f"{i+1:0>2d}"] = []
                            face[f"{i+1:0>2d}"].append(vert_index + 1)
                        i += 1

                    # This prevents it from parsing past largest_dimension
                    while i < largest_dimension:
                        try:
                            face[f"{i+1:0>2d}"].append(math.inf)
                        except:
                            face[f"{i+1:0>2d}"] = []
                            face[f"{i+1:0>2d}"].append(math.inf)
                        i += 1
                
                face_count = 0
                try:
                    face_count = len(face["01"])
                except:
                    face_count = 0 
                
                # Midpoints
                if op.use_midpoints:
                    if op.use_geo_x or op.use_geo_y or op.use_geo_z:
                        obj["midpoint"] = {}
                        midpoint = obj["midpoint"]
                    if op.use_geo_x:
                        midpoint["x"] = []
                    if op.use_geo_y:
                        midpoint["y"] = []
                    if op.use_geo_z:
                        midpoint["z"] = []
                    for polygon_element in data.polygons.values():
                        if op.use_geo_x:
                            midpoint["x"].append(polygon_element.center.x)
                        if op.use_geo_y:
                            midpoint["y"].append(polygon_element.center.y)
                        if op.use_geo_z:
                            midpoint["z"].append(polygon_element.center.z)
                
                # Normals
                if op.use_normals:
                    if op.use_geo_x or op.use_geo_y or op.use_geo_z:
                        obj["normal"] = {}
                        normal = obj["normal"]
                    if op.use_geo_x:
                        normal["x"] = []
                    if op.use_geo_y:
                        normal["y"] = []
                    if op.use_geo_z:
                        normal["z"] = []
                    for polygon_element in data.polygons.values():
                        if op.use_geo_x:
                            normal["x"].append(polygon_element.normal.x)
                        if op.use_geo_y:
                            normal["y"].append(polygon_element.normal.y)
                        if op.use_geo_z:
                            normal["z"].append(polygon_element.normal.z)
                    
                    # Attach Normals
                    if op.attach_normals:
                        
                        for i in range(face_count):
                            if op.use_geo_x:
                                normal["x"][i] = normal["x"][i] * 0.01 + midpoint["x"][i]
                            if op.use_geo_y:
                                normal["y"][i] = normal["y"][i] * 0.01 + midpoint["y"][i]
                            if op.use_geo_z:
                                normal["z"][i] = normal["z"][i] * 0.01 + midpoint["z"][i]
                            
                # Materials
                if op.use_materials:
                    obj["material"] = []
                    material = obj["material"]
                    for polygon_element in data.polygons.values():
                        material.append(polygon_element.material_index)
                
                
                
        # geometry ends here
        
        # Animation Export
        if op.use_animation:
            if op.use_location_x or op.use_location_y or op.use_location_z:
                obj["loc"] = {}
                loc = obj["loc"]
            if op.use_location_x:
                loc["x"] = []
            if op.use_location_y:
                loc["y"] = []
            if op.use_location_z:
                loc["z"] = []
            
            if op.use_rotation_x or op.use_rotation_y or op.use_rotation_z:
                obj["rot"] = {}
                rot = obj["rot"]
            if op.use_rotation_x:
                rot["x"] = []
            if op.use_rotation_y:
                rot["y"] = []
            if op.use_rotation_z:
                rot["z"] = []
            
            if op.use_scale_x or op.use_scale_y or op.use_scale_z:
                obj["scale"] = {}
                scale = obj["scale"]
            if op.use_scale_x:
                scale["x"] = []
            if op.use_scale_y:
                scale["y"] = []
            if op.use_scale_z:
                scale["z"] = []
            
            
            frame_initial = context.scene.frame_current
            frame_current = op.frame_start
            while frame_current <= op.frame_end:
                context.scene.frame_set(frame_current)
                context.view_layer.update()
                
                if op.use_location_global:
                    target = selected_object.matrix_world.to_translation()
                else:
                    target = selected_object.location
                if op.use_location_x:
                    loc["x"].append(target.x)
                if op.use_location_y:
                    loc["y"].append(target.y)
                if op.use_location_z:
                    loc["z"].append(target.z)
                
                convert_unit = 1.0
                if op.type_rotation_units == "DEG":
                    convert_unit = 180 / math.pi
                    
                if op.use_rotation_global:
                    target = selected_object.matrix_world.to_euler(op.type_rotation_euler)
                else:
                    target = selected_object.rotation_euler
                if op.use_rotation_x:
                    rot["x"].append(target.x * convert_unit)
                if op.use_rotation_y:
                    rot["y"].append(target.y * convert_unit)
                if op.use_rotation_z:
                    rot["z"].append(target.z * convert_unit)
                
                if op.use_scale_global:
                    target = selected_object.matrix_world.to_scale()
                else:
                    target = selected_object.scale
                if op.use_scale_x:
                    scale["x"].append(target.x)
                if op.use_scale_y:
                    scale["y"].append(target.y)
                if op.use_scale_z:
                    scale["z"].append(target.z)
                
                    
                
                frame_current += op.frame_step
            context.scene.frame_set(frame_initial)
        # animation ends here
    
    # The export is now concluded. Here are the functions used to compile the results above.
    
    # `console` is the final output that will be written to the file
    console = ""

    # `final_json` is the final dict that will be converted into `console`, if JSON mode is enabled
    final_json = [{"type": "folder", "title": "Blender Import", "id": "#folderId", "hidden": True, "collapsed": True}]
    
    # `file_push` creates either a newline in the text file, or a new column in the Desmos table
    def file_push(var_name, value_list):
        nonlocal console, final_json
        if op.type_output == "TXT":
            console += f"{var_name}={str_list(value_list)}\n"
        elif op.type_output == "JSON":
            current_column = {"latex": var_name, "values": [], "hidden": True, "id": "#Calc.controller.generateId()"}
            current_column["values"] = json_list(value_list)
            final_json[-1]["columns"].append(current_column)
            pass
        return
    
    # `simplify_num` takes a number, and rounds it, removing any unnecessary precision
    def simplify_num(num):
        if num == math.inf:
            return r"\infty"
        elif num == round(num):
            return str(round(num))
        
        num = float(num)

        if op.use_full_precision:
            stringified = f"{num}"
        else:
            stringified = f"{num:8f}"
        
        if stringified[0:2] == "0.":
            stringified = stringified[1:]
        elif stringified[0:3] == "-0.":
            stringified = "-" + stringified[2:]
        if "." in stringified:
            while stringified[-1] == "0":
                stringified = stringified[:-1]
        
        # final polish, cause sometimes there was a ".0" left behind.
        if float(stringified) == round(float(stringified)):
            stringied = str(round(float(stringied)))
        return stringified
    
    # `str_list` returns a plain-text list version of a number list, using `simply_num` rules 
    def str_list(x):
        output = ""
        add_comma = False
        for num in x:
            if add_comma:
                output += ","
            stringified = simplify_num(num)
            output += stringified
            add_comma = True
        return f"\\left[{output}\\right]"
    
    # `json_list` returns a genuine list which will be used by `final_json`. each element applies `simply_num` rules
    def json_list(x):
        output = []
        for num in x:
            output.append(simplify_num(num))
        return output
    
    # now its time to cycle through all of the data we've collected thus far and compile it into the file
    for name in final:  # get the prefix stuff
        if op.use_names:
            prefix = ""
            is_first_char = True
            for c in name:
                if c.isalnum():
                    if is_first_char:
                        c = c.upper()
                        is_first_char = False
                    prefix += c
        else:
            prefix = str(object_count)
            object_count += 1
        
        # this small portion is the equivalent of a "newline". time to write the next object please
        if op.type_output == "TXT":
            console += f"{name}\n"
        elif op.type_output == "JSON":
            final_json.append({"type": "text", "text": f'"{name}"', "folderId": "#folderId", "id": "#Calc.controller.generateId()"})
            final_json.append({"type": "table", "columns": [], "folderId": "#folderId", "id": "#Calc.controller.generateId()"})
        
        # push all of the data into the object, finally
        if op.use_vertices:
            for axis in final[name]["vert"]:
                var_name = ""
                var_name += f"{axis}_"
                if op.use_midpoints or op.use_normals:
                    var_name += "{Vertices"
                else:
                    var_name += "{"
                var_name += f"{prefix}" + "}"
                file_push(var_name, final[name]["vert"][axis])
            
            if "face" in final[name]:
                for index in final[name]["face"]:
                    var_name = ""
                    var_name += "f_{" + str(int(index))
                    if len(bpy.context.selected_objects) > 1:
                        if not op.use_names:
                            var_name += "Faces"
                        var_name += f"{prefix}"
                    elif op.use_names:
                        var_name += f"{prefix}"
                    var_name += "}"  
                    file_push(var_name, final[name]["face"][index])
            
                if "midpoint" in final[name]:
                    for axis in final[name]["midpoint"]:
                        var_name = ""
                        var_name += f"{axis}_"
                        var_name += "{Midpoints" + f"{prefix}" + "}"
                        file_push(var_name, final[name]["midpoint"][axis])
                        
                
                if "normal" in final[name]:
                    for axis in final[name]["normal"]:
                        var_name = ""
                        var_name += f"{axis}_"
                        var_name += "{Normals" + f"{prefix}" + "}"
                        file_push(var_name, final[name]["normal"][axis])
                
                if "material" in final[name]:
                    var_name = ""
                    var_name += "m_{Materials"
                    var_name += f"{prefix}" + "}"
                    file_push(var_name, final[name]["material"])
                
        if "loc" in final[name]:
            for axis in final[name]["loc"]:
                var_name = ""
                var_name += f"{axis}_"
                var_name += "{Location" + f"{prefix}" + "}"
                file_push(var_name, final[name]["loc"][axis])
        
        if "rot" in final[name]:
            for axis in final[name]["rot"]:
                var_name = ""
                var_name += f"{axis}_"
                var_name += "{Rotation" + f"{prefix}" + "}"
                file_push(var_name, final[name]["rot"][axis])
        
        if "scale" in final[name]:
            for axis in final[name]["scale"]:
                var_name = ""
                var_name += f"{axis}_"
                var_name += "{Scale" + f"{prefix}" + "}"
                file_push(var_name, final[name]["scale"][axis])
                
        if op.type_output == "TXT":
            console += "\n"
    
    if op.type_output == "TXT":
        console = "/* TIP: Here is an example of how you would use this add-on:\nhttps://www.desmos.com/calculator/u6xbg2i0xa\n*/\n\n" + console
    # at this point, `console` should be empty if JSON mode is enabled. time to finally use the Desmos API in its fullest
    if op.type_output == "JSON":
        dump = json.dumps(final_json)
        dump = dump.replace('"id": "#Calc.controller.generateId()"', '"id": Calc.controller.generateId()')
        dump = dump.replace('"folderId": "#folderId"', '"folderId": folderId')
        dump = dump.replace('"id": "#folderId"', '"id": folderId')
        console = f"""// ----------------- DISCLAIMER -------------------
// WARNING: It is EXTREMELY unsafe to inject unverified code like this into your browser. Please read the code CAREFULLY before you are ready to proceed with the injection.
// P.S. This will modify any unsaved graph in progress! You cannot undo this operation.


/* INSTRUCTIONS
To import a graph into Desmos, the API is used for the JSON injection.

1. Open your browser console (Hit F12 on your keyboard, or right click -> Inspect Element -> Console)
2. Paste these contents into your console field.
3. Wait. (Pasting can take a while if there is a lot of text to display.)
4. Hit enter.
5. Close/clear the console.
6. The graph is now imported!

This utilizes `Calc.setState()` to overwrite the graph's current condition.
To be clear, my code will perform two operations:
1. Store the JSON object as a local variable `blender`
2. Append the Calc expressions by using `blender`

Enjoy!
*/

folderId = Calc.controller.generateId();\nblender = {dump};\n"""
        console += """state = Calc.getState();
for (const expression of blender) {state.expressions.list.push(expression);}
Calc.setState(state);"""


    output_code = 0
    if is_face_too_large:
        output_code = 1

    return [console, output_code]



def menu_func_export(self, context):
    self.layout.operator(ExportDESMOS.bl_idname, text="Desmos Expressions by Heavenira (.txt)")


classes = (
    ExportDESMOS,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    #bpy.ops.export_scene.desmos('INVOKE_DEFAULT')
