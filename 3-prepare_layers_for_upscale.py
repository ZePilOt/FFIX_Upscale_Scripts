import os
import glob
import cv2
import shutil
import json
import numpy as np
from multiprocessing import Process, Pool, Manager

dir_path = os.path.dirname(os.path.realpath(__file__))

# Number of threads to use
NUM_THREADS = 12

# directory where the layers were extracted ib step 2.
FIELD_FOLDER = os.path.join(dir_path, "Extracted_Fields_Layers")

# directory where the images for upscaling will be created.
OUT_FOLDER = os.path.join(dir_path, "Combined_Fields_Layers")

# We are fixing missing informations in some layers. We output the correction mask in that folder.
OUT_FOLDER_FIX = os.path.join(dir_path, "Combined_Fields_Layers_BlackMaskFix")

fields_list = sorted(glob.glob(FIELD_FOLDER +"\\Field*"))

UNIQUE_LIST_PC = os.path.join(dir_path, "Unique_Fields_PC.json")

with open(UNIQUE_LIST_PC) as f:
	infos_pc = json.load(f)

def combined_layer_for_upscale(field_folder):

	info_file = os.path.join(field_folder, "infos.json")
	if os.path.exists(info_file) == False:
		return

	with open(info_file) as f:
		infos = json.load(f)

	field_id = infos["field_id"]
	
	previous_layer_without_overlap = None
	
	output_field = os.path.join(OUT_FOLDER, "Field"+ infos["field_id"])
	output_field_fix = os.path.join(OUT_FOLDER_FIX, "Field"+ infos["field_id"])

	# create output dir
	if not os.path.exists(output_field):
		os.makedirs(output_field)
	if not os.path.exists(output_field_fix):
		os.makedirs(output_field_fix)
	
	# testing all cameras for the field.
	for camera in infos_pc[field_id]:

		first_layer = True
	
		layers_static = []
		layers_generated = []

		# Filtering images for all static layer in the camera.
		for layer in infos[camera]["layers"]:
			if layer["camera_id"] != int(camera):
				print("What ?", layer["camera_id"], camera)
				continue

			# skip additive/multiply effects layers.
			if(layer["blend"]) == 1:
				continue

			# If the source is the PC version, we don't need to upscale it (text, ..)
			if(layer["source"]) == 0:
				continue

			# If the file has paralax, we output the information and continue.
			# The script doesn't something particular with parallax layers, there is only one field using it. (Field2916)
			# We still print it so we can check if we need to do something special !
			if(layer["has_parallax"]) == 1:
				print("parallax on", info_file)
					

			# We are isolating static layers for the moment.
			if(layer["is_static"] == 0):	
				continue
			
			layers_static.append(layer)

		# The actual process for static layers.
		for layer in layers_static:

			file_name = "Layer%i_%i.tiff" % (layer["camera_id"], layer["layer_number"])

			# combine static stuff
			if(layer["is_static"] == 1):
				layer_file = os.path.join(field_folder, file_name)

				# If it's not the first layer ...
				if first_layer == False:
					# We read the layer...
					foreground = cv2.imread(filename = layer_file, flags = cv2.IMREAD_UNCHANGED )
					rows,cols, num_channels = foreground.shape

					has_overlap = False
					has_overlap_other = False
						
					# We check if this layer overlap the previous layer (without compositing)
					
					comparaison_foreground = np.zeros((rows, cols , num_channels), np.uint8)
					comparaison_previous = np.zeros((rows, cols , num_channels), np.uint8)
					pixelCoverage = 0
					for i in range(rows):
						for j in range(cols):
							background_pixel_alpha = previous_layer_img[i,j][3]
							foreground_pixel_alpha = foreground[i,j][3]
							if foreground_pixel_alpha != 0 and background_pixel_alpha != 0:
								if ( previous_layer_img[i,j][0] != foreground[i,j][0] and
					 				 previous_layer_img[i,j][1] != foreground[i,j][1] and
					 				 previous_layer_img[i,j][2] != foreground[i,j][2] 
					 				):								
									comparaison_foreground[i,j] = foreground[i,j]
									comparaison_previous[i,j] = previous_layer_img[i,j]

									pixelCoverage += 1
					
					if pixelCoverage != 0:
						
						difference = (cv2.subtract(comparaison_foreground.astype(float), comparaison_previous.astype(float)))
						meanDiff = cv2.mean(difference)
						meanPx = ( abs(meanDiff[0]) + abs(meanDiff[1]) + abs(meanDiff[2]))
						
						if meanPx > 0.01:
							has_overlap = True

					# If we don't overlap at all, we can just compositing them together
					if has_overlap == False:

						channels = cv2.split(foreground)
						if len(channels) < 3:
							print("error", layer_file)

						# We are using the alpha channel of the current layer (so the PSX alpha)
						# If you want to use the PC alpha channel, you can edit replace this line with something like :
						# Read the alpha :

						# alpha_image = cv2.imread(filename = alpha_layer, flags = cv2.IMREAD_UNCHANGED )
						
						# Resize it to the PSX resolution, you can change the filtering too.
						
						# alpha_image = cv2.resize(alpha_image, (0,0), fx=0.5, fy=0.5, interpolation = cv2.INTER_NEAREST) 
						# alpha = alpha_image[0]

						alpha = channels[3]

						background = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(alpha))
						background = cv2.add(background, foreground)
						previous_layer_without_overlap = layer
						

						previous_layer_img = cv2.bitwise_and(previous_layer_img, previous_layer_img, mask=cv2.bitwise_not(alpha))
						previous_layer_img = cv2.add(previous_layer_img, foreground)


					else:
						#the layer on front overlap the one in the background.
						# we composite all the other layers without overlapping.
						altered_bg = background			

						for i in range(rows):
							for j in range(cols):
								background_pixel = background[i,j]
								foreground_pixel = foreground[i,j]
								if foreground_pixel[3] != 0 and background_pixel[3] == 0:
									altered_bg[i,j] = foreground_pixel

						for other_layer in layers_static:
							if other_layer["layer_number"] > layer["layer_number"]:
								
								other_file_name = "Layer%i_%i.tiff" % (layer["camera_id"], other_layer["layer_number"])
								other_layer_file = os.path.join(field_folder, other_file_name)
								
								other_foreground = cv2.imread(filename = other_layer_file, flags = cv2.IMREAD_UNCHANGED )
								for i in range(rows):
									for j in range(cols):
										background_pixel = altered_bg[i,j]
										foreground_pixel = other_foreground[i,j]
										if foreground_pixel[3] != 0 and background_pixel[3] == 0:
											altered_bg[i,j] = foreground_pixel								

						layers_generated.append(previous_layer_without_overlap["layer_number"])


						if os.path.exists(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, previous_layer_without_overlap["layer_number"]))) == False:
							cv2.imwrite(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, previous_layer_without_overlap["layer_number"])), altered_bg)

						
						channels = cv2.split(foreground)
						if len(channels) < 3:
							print("error", layer_file)
						alpha = channels[3]
						background = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(alpha))
						background = cv2.add(background, foreground)
						
						if layer["layer_number"] == layers_static[-1]["layer_number"]:
							layers_generated.append(layer["layer_number"])

							if os.path.exists(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, layer["layer_number"]))) == False:
								cv2.imwrite(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, layer["layer_number"])), background)
						
						previous_layer_without_overlap = layer
					
						previous_layer_img = foreground


				else:
					# It is the first layer ... 
					previous_layer_without_overlap = layer

					# Reading the background.
					background = cv2.imread(filename = layer_file, flags = cv2.IMREAD_UNCHANGED )	
					previous_layer_img = background
					rows,cols, num_channels = background.shape
					# check large area of missing pixels.
					numBlack = 0
					pixelsBlack = []
					for i in range(rows):
						for j in range(cols):
							background_pixel = background[i,j]
							if background_pixel[3] != 0:
								if background_pixel[0] == 0 and background_pixel[1] == 0 and background_pixel[2] == 0:

									pixelsBlack.append((i,j))




					if len(pixelsBlack) > 200:						
						# we have a large amount of missing pixels, We try to fix these.

						previous_num_black = numBlack
						
						other_layers_img = []
						goodLayerFound = []
						for other_layer in infos[camera]["layers"]:
							if(other_layer["blend"]) == 1:
								continue

							if(other_layer["source"]) == 0:
								continue

							# We check if we have the info in another layer, static or animated.
							if layer["layer_number"] != other_layer["layer_number"]:
								other_file_name = "Layer%i_%i.tiff" % (other_layer["camera_id"], other_layer["layer_number"])
								other_layer_file = os.path.join(field_folder, other_file_name)
								other_img = cv2.imread(filename = other_layer_file, flags = cv2.IMREAD_UNCHANGED )
								
								numPixelsFixed = 0
								for pixel in pixelsBlack :
									other_pixel = other_img[pixel[0],pixel[1]]
									if other_pixel[3] != 0:
										if other_pixel[0] != 0 and other_pixel[1] != 0 and other_pixel[2] != 0:
											numPixelsFixed += 1

								if numPixelsFixed >= 200:
									
									goodLayerFound.append(other_img)

						# We found other layers to fix these black pixels...
						if len(goodLayerFound) != 0 :

							mask_image = np.zeros((rows, cols ,3), np.uint8)
							
							# We update the layer with the fixed pixels.
							for goodLayer in goodLayerFound:
								for pixel in pixelsBlack :
									if goodLayer[pixel][3] != 0 :
										mask_image[pixel] = (255,255,255)
										background[pixel] = goodLayer[pixel]
												

							# We output the mask of correction.
							file_name_mask = "Layer_MaskFix%i_%i.png" % (layer["camera_id"], layer["layer_number"])
							file_mask = os.path.join(output_field_fix, file_name_mask)


							cv2.imwrite(file_mask, mask_image)



				# Next layer won't be the first one, obviously...
				first_layer = False



		
		if len(layers_generated) == 0 :
			out_static_file = os.path.join(output_field, "static_layers_%s.png" % camera )
			if os.path.exists(out_static_file) == False:
				cv2.imwrite(out_static_file, background)
			statics_have_overlapping = False
			infos[camera]["static_has_overlap"] = False
		elif len(layers_generated) == 1 :
			out_static_file = os.path.join(output_field, "static_layers_%s_%s.png" % (camera, layer["layer_number"] ))
			if os.path.exists(out_static_file) == False:
				cv2.imwrite(out_static_file, background)
			statics_have_overlapping = True
			infos[camera]["static_has_overlap"] = True
		else:
			statics_have_overlapping = True
			infos[camera]["static_has_overlap"] = True


		
		# then animation layers
		for layer in infos[camera]["layers"]:

			if layer["camera_id"] != int(camera):
				print("What ?", layer["camera_id"], camera)
				continue
			# still skip lighting effects
			if(layer["blend"]) == 1:
				continue

			if(layer["is_static"] == 0):

				file_name = "Layer%i_%i.tiff" % (layer["camera_id"], layer["layer_number"])
				layer_file_anim = os.path.join(field_folder, file_name)
				frame = cv2.imread(filename = layer_file_anim, flags = cv2.IMREAD_UNCHANGED )		
				
				channels = cv2.split(frame)
				alpha = channels[3]


				if statics_have_overlapping == False:
					composited_frame = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(alpha))
					composited_frame = cv2.add(frame, composited_frame)
					
				else:
					
					if layer["layer_number"] < layers_generated[0]:
						layer_file_to_load = os.path.join(output_field, "static_layers_%s_%i.png" % (camera, layers_generated[0]))

					elif layer["layer_number"] > layers_generated[-1]:
						layer_file_to_load = os.path.join(output_field, "static_layers_%s_%i.png" % (camera, layers_generated[-1]))
					else:
						for static_layer in layers_generated:
							if static_layer < layer["layer_number"]:
								
								layer_file_to_load = os.path.join(output_field, "static_layers_%s_%i.png" % (camera, static_layer))


					background = cv2.imread(filename = layer_file_to_load, flags = cv2.IMREAD_UNCHANGED )		

					composited_frame = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(alpha))
					composited_frame = cv2.add(frame, composited_frame)
				
				if os.path.exists(os.path.join(output_field, "anim_layer_%i_%i.png" % (int(camera), layer["layer_number"] ))) == False:

					cv2.imwrite(os.path.join(output_field, "anim_layer_%i_%i.png" % (int(camera), layer["layer_number"] )), composited_frame)

	info_file = os.path.join(output_field, "infos.json")
	with open(info_file, "w") as write_file:
		json.dump(infos, write_file, indent=4)

if __name__ == '__main__':


	pool = Pool(NUM_THREADS)
	pool.map(combined_layer_for_upscale, fields_list)
