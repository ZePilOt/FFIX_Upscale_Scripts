import os
import sys
import glob
import cv2
import shutil
import json
import numpy as np
from multiprocessing import Process, Pool, Manager

dir_path = os.path.dirname(os.path.realpath(__file__))

# Number of threads to use
NUM_THREADS = 12

EXTRACTED_FIELD_FOLDER = os.path.join(dir_path, "Extracted_Fields_Layers")

# The combined folder
COMBINED_FIELD_FOLDER = os.path.join(dir_path, "Combined_Fields_Layers")

# THe upscaled folder
UPSCALED_FIELD_FOLDER = os.path.join(dir_path, "Combined_Upscaled_Fields_Layers")

# The blank pixel correction mask
BLACK_AREA_MASK_FOLDER = os.path.join(dir_path, "Combined_Fields_Layers_BlackMaskFix")

# Alpha..
ALPHA_FOLDER = os.path.join(dir_path, "Extracted_Fields_Alpha_Layers")

# And final output
OUT_FOLDER = os.path.join(dir_path, "Upscaled_Fields_Layers")


UNIQUE_LIST_PC = os.path.join(dir_path, "Unique_Fields_PC.json")
with open(UNIQUE_LIST_PC) as f:
	infos_pc = json.load(f)


def prepare_for_hades(field_folder):
	

	info_file = os.path.join(field_folder, "infos.json")
	if os.path.exists(info_file) == False:
		print("missing", info_file)
		return

	with open(info_file) as f:
		infos = json.load(f)

	field_id = infos["field_id"]

	info_upscale = os.path.join(COMBINED_FIELD_FOLDER, "Field"+infos["field_id"], "infos.json")
	if os.path.exists(info_file) == False:
		print("error")
		return
	with open(info_upscale) as f:
		info_upscale = json.load(f)	


	# create output dir
	output_field = os.path.join(OUT_FOLDER, "Field"+infos["field_id"])
	if not os.path.exists(output_field):
		os.makedirs(output_field)


	
	for camera in infos_pc[field_id]:
		
		# Get all static layers
		static_layers = os.path.join(UPSCALED_FIELD_FOLDER, "Field%s" % infos["field_id"], "static_layers_%i_*.png" % (int(camera)))
		static_layers = sorted(glob.glob(static_layers))
		map_static_layers = {}
		for l in static_layers:
			bn = os.path.basename(l)
			layer = bn.split(".")[0].split("_")[-1]
			
			map_static_layers[int(layer)] = l

		first_layer = True

		# We iterate over all the original layers.
		for layer in infos[camera]["layers"]:
			
		
			file_name = "Layer%i_%i.tiff" % (layer["camera_id"], layer["layer_number"])
			output_path = os.path.join(output_field, file_name  )
			
			if os.path.exists(output_path) : 
				pass#continue

			# The layer is an effect layer, we do a resize.
			if(layer["blend"]) == 1 or layer["source"] == 0:
				#stupid resizing	
				layer_file = os.path.join(field_folder.replace(COMBINED_FIELD_FOLDER, EXTRACTED_FIELD_FOLDER), file_name)
				img = cv2.imread(filename = layer_file, flags = cv2.IMREAD_UNCHANGED )
				img = cv2.resize(img, (0,0), fx=2.0, fy=2.0, interpolation = cv2.INTER_NEAREST) 
				output_path = os.path.join(output_field, file_name  )
				cv2.imwrite(output_path, img)

			# Static layer....
			elif(layer["is_static"] == 1):

				# The current layer has a specific static file, we use it.
				if layer["layer_number"] in map_static_layers:
					upscaled_static_layer_file = map_static_layers[layer["layer_number"]]


				# We don't have a specific file, but we have several candidate, so we find the closest one (but never at a lower depth)
				elif len(map_static_layers) != 0:
					fi = filter(lambda x : x >= layer["layer_number"], map_static_layers)
					
					try:
						result = min(fi)
						upscaled_static_layer_file = map_static_layers[result]
						print(upscaled_static_layer_file)
					except ValueError:
						upscaled_static_layer_file =  os.path.join(UPSCALED_FIELD_FOLDER, "Field%s" % infos["field_id"], "static_layers_%i.png" % (layer["camera_id"]))
						if os.path.exists(upscaled_static_layer_file) == False:
							maximum = max(map_static_layers, key=map_static_layers.get) 
							upscaled_static_layer_file =  map_static_layers[maximum]

				# We don't have a specific file, but we only have one candidate (no overlap), we use it.
				else:
					upscaled_static_layer_file =  os.path.join(UPSCALED_FIELD_FOLDER, "Field%s" % infos["field_id"], "static_layers_%i.png" % (layer["camera_id"]))

	
				layer_file = os.path.join(field_folder, file_name)

				# Check, shouldn't happens if everything was good.
				if os.path.exists(upscaled_static_layer_file) == False:
					print("Error : ",upscaled_static_layer_file, "Doesn't exist !")
					return

				# Read the image
				img_upscaled = cv2.imread(filename = upscaled_static_layer_file, flags = cv2.IMREAD_UNCHANGED )
			
				# Read the blank pixel mask and re-apply it. You can skip it if you don't want to.
				black_mask_path = upscaled_static_layer_file.replace(UPSCALED_FIELD_FOLDER, BLACK_AREA_MASK_FOLDER).replace("static_layers_", "Layer_MaskFix")
				if os.path.exists(black_mask_path):
					img_blck = cv2.imread(filename = black_mask_path, flags = cv2.IMREAD_UNCHANGED )
					img_blck = cv2.resize(img_blck, (0,0), fx=4.0, fy=4.0, interpolation = cv2.INTER_NEAREST) 
					rows,cols, num_channels = img_upscaled.shape
					for i in range(rows):
						for j in range(cols):
							if img_blck[i,j][0] == 255:
								img_upscaled[i,j][0] = 0
								img_upscaled[i,j][1] = 0
								img_upscaled[i,j][2] = 0


				# If you want to use another alpha source (here, PC version) for the final masking, you can switch it here (see comments in the step 3.)
				# for exemple, if you want to re-use the PSX mask :

				# alpha_layer_file = os.path.join(COMBINED_FIELD_FOLDER, "Field%s" % infos["field_id"], file_name)
				alpha_layer_file = os.path.join(ALPHA_FOLDER, "Field%s" % infos["field_id"], file_name)

				img_alpha = cv2.imread(filename = alpha_layer_file, flags = cv2.IMREAD_UNCHANGED )

				# Rescale the alpha. If the source is the PSX alpha, change fx & fy to 4.0. You can change the interpolation too and add other process if you like.
				img_alpha = cv2.resize(img_alpha, (0,0), fx=2.0, fy=2.0, interpolation = cv2.INTER_NEAREST) 
				
				rows,cols, num_channels = img_alpha.shape
				
				a = cv2.split(img_alpha)[0]
				
				if img_upscaled.shape[2] == 3:
					r,g,b = cv2.split(img_upscaled)
				else:
					r,g,b, _ = cv2.split(img_upscaled)
				
				img_upscaled = cv2.merge((r,g,b,a))
				output_path = os.path.join(output_field, file_name  )

				kernel = np.ones((5,5), np.uint8) 
				a_erosion = cv2.erode(a, kernel, iterations=1) 
				#a_dilation = cv2.dilate(a, kernel, iterations=1)
				mask_overlap = cv2.subtract(a, a_erosion)

				# check if we have a animation going in between...
				if True:			
					for anim_layer in infos[camera]["layers"]:
						if anim_layer["is_static"] == 0 and anim_layer["is_first_of_anim"] == 1 and anim_layer["source"] == 1 and anim_layer["distance"] > layer["distance"]:
							#upscaled_anim_layer_file =  os.path.join(UPSCALED_FIELD_FOLDER, "Field%s" % infos["field_id"], ))
							anim_file_name = "Layer%i_%i.tiff" % (anim_layer["camera_id"], anim_layer["layer_number"])
							alpha_layer_anim_file = os.path.join(ALPHA_FOLDER, "Field%s" % infos["field_id"], anim_file_name)
							img_alpha_anim = cv2.imread(filename = alpha_layer_anim_file, flags = cv2.IMREAD_UNCHANGED )
							img_alpha_anim = cv2.resize(img_alpha_anim, (0,0), fx=2.0, fy=2.0, interpolation = cv2.INTER_NEAREST)
							img_alpha_anim = cv2.split(img_alpha_anim)[0] 

							overlap_alpha = cv2.multiply(img_alpha_anim, a_erosion)
							count = cv2.countNonZero(overlap_alpha)
							if count != 0:

								layer_anim_file = os.path.join(UPSCALED_FIELD_FOLDER, "Field%s" % infos["field_id"], "anim_layer_%s_%i.png" % (camera, anim_layer["layer_number"]))
								img_anim_upscale = cv2.imread(filename = layer_anim_file, flags = cv2.IMREAD_UNCHANGED )
								has_overlap = False
								for i in range(rows):
									for j in range(cols):
										if mask_overlap[i,j] != 0 and img_alpha_anim[i,j] != 0:
											has_overlap = True
											img_upscaled[i,j] =  img_anim_upscale[i,j]

								if has_overlap:
									print(output_path, "has", layer_anim_file) 



				
				cv2.imwrite(output_path, img_upscaled)

			else:
				# Animated layers

				# Alpha file, see comment from static files to switch the alpha channel source.
				alpha_layer_file = os.path.join(ALPHA_FOLDER, "Field%s" % infos["field_id"], file_name)
				upscaled_static_layer_file = os.path.join(UPSCALED_FIELD_FOLDER, "Field%s" % infos["field_id"], "anim_layer_%i_%i.png" % (layer["camera_id"], layer["layer_number"] ))

				if os.path.exists(upscaled_static_layer_file) == False:
					print("Error : ",upscaled_static_layer_file, "Doesn't exist !")
					return

				img_alpha = cv2.imread(filename = alpha_layer_file, flags = cv2.IMREAD_UNCHANGED )
				img_upscaled = cv2.imread(filename = upscaled_static_layer_file, flags = cv2.IMREAD_UNCHANGED )
				
				rows,cols, num_channels = img_alpha.shape
				img_alpha = cv2.resize(img_alpha, (0,0), fx=2.0, fy=2.0, interpolation = cv2.INTER_NEAREST) 

				if img_upscaled.shape[2] == 3:
					r,g,b = cv2.split(img_upscaled)
				else:
					r,g,b, _ = cv2.split(img_upscaled)

				a = cv2.split(img_alpha)[0]
				img_upscaled = cv2.merge((r,g,b,a))

				output_path = os.path.join(output_field, file_name  )
				cv2.imwrite(output_path, img_upscaled)



if __name__ == '__main__':

	pool = Pool(NUM_THREADS)
	fields_list = sorted(glob.glob(COMBINED_FIELD_FOLDER +"\\Field*"))
	pool.map(prepare_for_hades, fields_list)
