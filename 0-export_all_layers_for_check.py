import os
import glob
import cv2
import shutil
import json
dir_path = os.path.dirname(os.path.realpath(__file__))


PC_FOLDER = os.path.join(dir_path, "PC_Extracted_Fields_Background")
OUT_FOLDER = os.path.join(dir_path, "PC_LAYERS_FOR_CHECKING")



img_list = sorted(glob.glob(PC_FOLDER+"\\*.tiff"))

file_matching = {}
file_matching["source_to_field"] = dict()
file_matching["field_to_source"] = dict()

for img_PC in img_list:
	print(img_PC)
	with open(img_PC + ".info") as f:
		tile_PC = f.readline().strip()
		info_PC = f.readlines()

	orig_field_number = os.path.basename(img_PC).replace(".tiff", "").replace("PC_", "")
	file_matching["source_to_field"][orig_field_number] = int(tile_PC)
	file_matching["field_to_source"][int(tile_PC)] = orig_field_number
	

	print("Processing", os.path.basename(img_PC), "tile", tile_PC)


	# create output dir
	output_field = os.path.join(OUT_FOLDER, "Field"+tile_PC)
	if not os.path.exists(output_field):
		os.makedirs(output_field)

	ret, layers_PC = cv2.imreadmulti(filename = img_PC, flags = cv2.IMREAD_UNCHANGED )	

	if len(layers_PC) != len(info_PC):
		print(img_PC)
		print(len(layers_PC), len(line_info_PC))

		
	infos = dict()
	infos["field_id"] = tile_PC
	infos["original_file_PC"] = os.path.basename(img_PC)
	infos["layers"] = []

	for i in range(0, len(layers_PC)):

		layer = dict()

		infos_layer = info_PC[i].strip().split(" ")
		layer_blend = int(infos_layer[7])
		layer_number = infos_layer[0]
		layer_camera = infos_layer[1]

		layer["layer_number"] = int(layer_number)
		layer["layer_id"] = int(infos_layer[2])
		layer["camera_id"] = int(layer_camera)
		layer["blend"] = int(layer_blend)

		layer["tile_amount"] = int(infos_layer[3])
		layer["distance"] = int(infos_layer[4])
		layer["has_parallax"] = int(infos_layer[5])
		layer["is_static"] = int(infos_layer[6])
		layer["is_attached"] = int(infos_layer[8])
		layer["is_first_of_anim"] = int(infos_layer[9])
		layer["is_looping"] = int(infos_layer[10])

		outName = "Layer" + layer_camera + "_" + layer_number + ".tiff"

			
		imgColor = layers_PC[i]
		print(os.path.join(output_field, outName))
		cv2.imwrite(os.path.join(output_field, outName) , imgColor)




	

