import os
import glob
import cv2
import shutil
import json
from multiprocessing import Process, Pool, Manager

# Number of threads to use
NUM_THREADS = 12

dir_path = os.path.dirname(os.path.realpath(__file__))

# directory where the TIFF files for the PC background are located.
PC_FOLDER = os.path.join(dir_path, "PC_Extracted_Fields_Background")

# directory where the TIFF files for the PSX background are located.
PSX_FOLDER = os.path.join(dir_path, "PSX_Extracted_Fields_Background")

# directory where the layers for the backgrounds will be extracted.
OUT_FOLDER = os.path.join(dir_path, "Extracted_Fields_Layers")

# directory where alpha channels will be extracted
OUT_ALPHA_FOLDER = os.path.join(dir_path, "Extracted_Fields_Alpha_Layers")

# Reading info files form Step 1.
with open("Unique_Fields_PC.json", "r") as read_file:
	Field_PC_info = json.load(read_file)

with open("Unique_Fields_PSX.json", "r") as read_file:
	Field_PSX_info = json.load(read_file)

with open("match_PC_PSX.json", "r") as read_file:
	PC_to_PSX = json.load(read_file)

def process_tile(tile_PC):

	field_info = Field_PC_info[tile_PC].copy()

	field_info["field_id"] = tile_PC


	output_field = os.path.join(OUT_FOLDER, "Field" + tile_PC)
	if not os.path.exists(output_field):
		os.makedirs(output_field)

	output_alpha_field = os.path.join(OUT_ALPHA_FOLDER, "Field" + tile_PC)

	if not os.path.exists(output_alpha_field):
		os.makedirs(output_alpha_field)

	for camera in Field_PC_info[tile_PC]:
		camera_info = Field_PC_info[tile_PC][camera]
		img_PC = camera_info["img"]

		# read all the layers from the PC version. 
		ret, layers_PC = cv2.imreadmulti(filename = img_PC, flags = cv2.IMREAD_UNCHANGED )
		
		if not tile_PC in PC_to_PSX:
			print("missing PSX for tile", tile_PC)
			continue
		
		matching_psx_field = PC_to_PSX[tile_PC][camera]
		img_PSX = Field_PSX_info[matching_psx_field][camera]["img"]

		# read all the layers from the PSX version. 
		ret, layers_PSX = cv2.imreadmulti(filename = img_PSX, flags = cv2.IMREAD_UNCHANGED )
		img_PSX_relative = os.path.relpath(img_PSX, PSX_FOLDER)

		field_info[camera]["original_file_PSX"] = img_PSX_relative

		for layer in camera_info["layers"] :
			# Prepare info files for each field, so we know where the layer come from, and what it is exactly.
			has_a_color = False
			layer_number = layer["layer_number"]
			layeR_id = layer["layer_id"]
			layer_blend = layer["blend"]
			outName = "Layer%s_%i.tiff" % (camera, layer_number)
			out_alpha = os.path.join(output_alpha_field, outName)

			# For additive or multiply layers, we use the PC source, 
			# as the shaders for the PC port are meant for these, and are different in the PSX version.
			if layer_blend != 0 :
				field_info[camera]["layers"][layer_number]["source"] = 0
				imgColor = layers_PC[layer_number]
				has_a_color = True
			else:
					# If it's not an effect layer, we use preferably the PSX version.
					if (len(layers_PSX) > layer_number) :
						imgColor = layers_PSX[layer_number]
						has_a_color = True
						field_info[camera]["layers"][layer_number]["source"] = 1

			# If we don't find a corresponding PSX layer (ie. text for other languages), we use the PC version.
			if has_a_color == False:
				imgColor = layers_PC[layer_number]
				field_info[camera]["layers"][layer_number]["source"] = 0

			# write the color of the files. Source depend of previous tests.
			cv2.imwrite(os.path.join(output_field, outName) , imgColor)

	 		# write the alpha of the files. Source is PC.
	 		# For PSX alpha, it's still embeded in the color layer. You can use the alpha channel in OUT_FOLDER directly.
			if os.path.exists(out_alpha) == False:
				channels = cv2.split(layers_PC[layer_number])
				alpha = channels[3]
				alphaColor = cv2.cvtColor(alpha, cv2.COLOR_GRAY2RGB)
				cv2.imwrite(out_alpha , alphaColor)

	# write info files for each field. 
	info_file = os.path.join(output_field, "infos.json")
	with open(info_file, "w") as write_file:
		json.dump(field_info, write_file, indent=4)



if __name__ == '__main__':

	pool = Pool(NUM_THREADS)
	pool.map(process_tile, Field_PC_info)
		