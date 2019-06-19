import os
import glob
import cv2
import shutil
import json
import numpy as np
import math
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

GROUP_STATIC = []

def imwrite(out_file, img):
	_,_,_,a = cv2.split(img)
	numPixels = cv2.countNonZero(a)

	if numPixels != img.shape[0] * img.shape[1]:
		kernel = np.ones((2,2),np.uint8)
		#print("alpha", image_source)
		img2 = cv2.dilate(img ,kernel ,iterations = 1)
		img2 = cv2.bitwise_and(img2, img2, mask=cv2.bitwise_not(a))
		img = cv2.add(img,img2)
		

	cv2.imwrite(out_file, img)	

def process_static_layers(layers_static, field_folder, camera, infos, output_field, output_field_fix, idx = 0, fixBlack = True, blackBackground = False):

	layers_generated = []
	layer_static_count = 0
	first_layer = True
	# The actual process for static layers.
	for layer in layers_static:

		file_name = "Layer%i_%i.tiff" % (layer["camera_id"], layer["layer_number"])

		# combine static stuff
		if True:
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

					if layer_static_count == len(layers_static) - 1 :
						if len(layers_generated) > 0:
							layers_generated.append((layer["layer_number"], layer["layer_id"]))
							out_static_file = os.path.join(output_field, "static_layers_%s_%s.png" % (camera, layer["layer_number"] ))
							if os.path.exists(out_static_file) == False:
								imwrite(out_static_file, background)

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


					layers_generated.append((previous_layer_without_overlap["layer_number"], previous_layer_without_overlap["layer_id"]))


					if os.path.exists(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, previous_layer_without_overlap["layer_number"]))) == False:
						imwrite(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, previous_layer_without_overlap["layer_number"])), altered_bg)

					
					channels = cv2.split(foreground)
					if len(channels) < 3:
						print("error", layer_file)
					alpha = channels[3]
					background = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(alpha))
					background = cv2.add(background, foreground)
					
					if layer["layer_number"] == layers_static[-1]["layer_number"]:
						layers_generated.append((layer["layer_number"], layer["layer_id"]))

						if os.path.exists(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, layer["layer_number"]))) == False:
							imwrite(os.path.join(output_field, "static_layers_%s_%i.png" % (camera, layer["layer_number"])), background)
					
					previous_layer_without_overlap = layer
				
					previous_layer_img = foreground


			else:
				# It is the first layer ... 
				previous_layer_without_overlap = layer

				# Reading the background.
				background = cv2.imread(filename = layer_file, flags = cv2.IMREAD_UNCHANGED )	

				if blackBackground == True:

					rows, cols, _ = background.shape 
					backgroundBlack = np.zeros(background.shape, np.uint8)
					for i in range(rows):
						for j in range(cols):
							backgroundBlack[i,j] = background[i,j]
							backgroundBlack[i,j][3] = 255


					background = backgroundBlack

				previous_layer_img = background
				rows,cols, num_channels = background.shape
				# check large area of missing pixels.
				numBlack = 0
				pixelsBlack = []
				if fixBlack == True:
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
					
					otherLayers =infos[camera]["layers"]

					if infos["field_id"] == "1000":
						otherLayers = [infos[camera]["layers"][4], infos[camera]["layers"][8], infos[camera]["layers"][12]]



					for other_layer in otherLayers:
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


						imwrite(file_mask, mask_image)



			# Next layer won't be the first one, obviously...
			first_layer = False


		layer_static_count += 1
	
	if len(layers_generated) == 0 :

		out_static_file = os.path.join(output_field, "static_layers_%s.png" % camera )
		if idx != 0:
			out_static_file = os.path.join(output_field, "static_layers_%s_%i.png" % (camera, idx ))
		if os.path.exists(out_static_file) == False:
			imwrite(out_static_file, background)
		statics_have_overlapping = False
		infos[camera]["static_has_overlap"] = False
	elif len(layers_generated) == 1 :

		out_static_file = os.path.join(output_field, "static_layers_%s_%s.png" % (camera, layer["layer_number"] ))
		if os.path.exists(out_static_file) == False:
			imwrite(out_static_file, background)
		statics_have_overlapping = True
		layers_generated.append((layer["layer_number"], layer["layer_id"]))
		infos[camera]["static_has_overlap"] = True
	else:
		statics_have_overlapping = True
		infos[camera]["static_has_overlap"] = True

	return layers_generated, statics_have_overlapping, background



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

		fixBlack = True
		blackBackground = False

		num_layers = len(infos[camera]["layers"])
		
	
		layers_static = []
		layers_static_group = []
		if field_id == "766" or field_id == "1055" or field_id == "813":
			layers_static_group.append([])
			layers_static_group.append([])

		if field_id == "931":
			layers_static_group.append([])
			layers_static_group.append([])
			layers_static_group.append([])
			


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
			
			# special case for field 766 : They are actually two backgrounds, one with lighting, the other without.
			if field_id == "766":
				if (layer["layer_number"] % 2) == 0:
					layers_static_group[0].append(layer)
				else:
					layers_static_group[1].append(layer)
			
			if field_id == "1055":
				# to solve background compositing being ugly
				if layer["layer_number"] < 2:
					layers_static_group[0].append(layer)
				else:
					layers_static_group[1].append(layer)				

			if field_id == "813":
				# to solve background compositing being ugly
				if layer["layer_number"] < 4:
					layers_static_group[0].append(layer)
				else:
					layers_static_group[1].append(layer)


			if field_id == "931":
				# to solve background compositing being ugly
				if layer["layer_number"] == 0:
					
					layers_static_group[0].append(layer)
					#layers_static_group[1].append(layer)
					#layers_static_group[2].append(layer)
				if layer["layer_number"] <= 2:
					layers_static_group[1].append(layer)
				else:
					layers_static_group[2].append(layer)

		
		if field_id == "2908":
			# we need a animated layer ...
			layers_static.insert(0, infos[camera]["layers"][2])

		if field_id == "1000":
			blackBackground = True
			#layers_static.insert(1, infos[camera]["layers"][7])
			#layers_static.insert(2 ,infos[camera]["layers"][11])
			for l in layers_static:
				print(l)
	
		if field_id == "931":
			fixBlack = False
			blackBackground = True

		if len(layers_static_group) != 0:
			i = 0
			for group in layers_static_group:
				layers_generated, statics_have_overlapping, background = process_static_layers(group, field_folder, camera, infos, output_field, output_field_fix, i, fixBlack = fixBlack, blackBackground =blackBackground)
				i = i + 1
		else:

			layers_generated, statics_have_overlapping, background = process_static_layers(layers_static, field_folder, camera, infos, output_field, output_field_fix, fixBlack = fixBlack, blackBackground = blackBackground)

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

					specialCase = False

					# special case. Could be detected, but it's easier this way.
					if infos["field_id"] == "357":
						composited_frame = background

						if layer["layer_number"] >= 13 and layer["layer_number"] <= 28:			
								specialCase = True
								offsetAnimOmbre = 7 + ( layer["layer_number"] - 13 )
								if offsetAnimOmbre >= (7 + 8):
									offsetAnimOmbre -= 8									
								if offsetAnimOmbre >= (7 + 4):
									offsetAnimOmbre -= 4

							

								layer_file_to_load = os.path.join(field_folder, "Layer0_%i.tiff" % offsetAnimOmbre)
								background_add = cv2.imread(filename = layer_file_to_load, flags = cv2.IMREAD_UNCHANGED )	
								channels_add = cv2.split(background_add)
								composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(channels_add[3]))
								composited_frame = cv2.add(background_add, composited_frame)


								if  layer["layer_number"] <= 24:
									# 25 to 28
									offsetOtherRoue = layer["layer_number"] + 12
									if offsetOtherRoue > 28 + 4:
									 	offsetOtherRoue -= 8									
									if offsetOtherRoue > 28:
									 	offsetOtherRoue -= 4	

									layer_file_to_load = os.path.join(field_folder, "Layer0_%i.tiff" % offsetOtherRoue)
									background_add = cv2.imread(filename = layer_file_to_load, flags = cv2.IMREAD_UNCHANGED )	
									channels_add = cv2.split(background_add)
									composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(channels_add[3]))
									composited_frame = cv2.add(background_add, composited_frame)

								
								composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(alpha))
								composited_frame = cv2.add(frame, composited_frame)		


						if layer["layer_number"] >= 17 and layer["layer_number"] <= 28:	
								specialCase = True

								offsetAnimRoue = 13 + ( layer["layer_number"] - 13 )
								if offsetAnimRoue >= (13 + 8):
									offsetAnimRoue -= 8									
								if offsetAnimRoue >= (13 + 4):
									offsetAnimRoue -= 4


								layer_file_to_load = os.path.join(field_folder, "Layer0_%i.tiff" % offsetAnimRoue)
								background_add = cv2.imread(filename = layer_file_to_load, flags = cv2.IMREAD_UNCHANGED )	
								channels_add = cv2.split(background_add)
								composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(channels_add[3]))
								composited_frame = cv2.add(background_add, composited_frame)
								
								composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(alpha))
								composited_frame = cv2.add(frame, composited_frame)	

						if layer["layer_number"] >= 25 and layer["layer_number"] <= 28:		
							pass							
								#layer_file_to_load = os.path.join(field_folder, "Layer0_%i.tiff" % offsetAnimRoue)
								 #background_add = cv2.imread(filename = layer_file_to_load, flags = cv2.IMREAD_UNCHANGED )	
								#channels_add = cv2.split(background_add)
								#composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(channels_add[3]))
								#composited_frame = cv2.add(background_add, composited_frame)
								
								# composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(alpha))
								# composited_frame = cv2.add(frame, composited_frame)																

					if infos["field_id"] == "1000" :

						composited_frame = background
						if layer["layer_number"] >= 4 and layer["layer_number"] <= 7:
							specialCase = True
							offsetAnimTree = 8 + ( layer["layer_number"] - 4 )


						if layer["layer_number"] >= 8 and layer["layer_number"] <= 11:
							specialCase = True
							offsetAnimTree = 4 + ( layer["layer_number"] - 8 )

						
						if specialCase:
							layer_file_to_load = os.path.join(field_folder, "Layer0_%i.tiff" % offsetAnimTree)
							background_add = cv2.imread(filename = layer_file_to_load, flags = cv2.IMREAD_UNCHANGED )	
							channels_add = cv2.split(background_add)
							composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(channels_add[3]))
							composited_frame = cv2.add(background_add, composited_frame)

							composited_frame = cv2.bitwise_and(composited_frame, composited_frame, mask=cv2.bitwise_not(alpha))
							composited_frame = cv2.add(frame, composited_frame)		

					if not specialCase:
						composited_frame = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(alpha))
						composited_frame = cv2.add(frame, composited_frame)

				else:

					minLayerId = 9999

					for x in layers_generated:
						if x[1] < minLayerId:
							minLayerId = x[1]
					maxLayerId = 0
					for x in layers_generated:
						if x[1] > minLayerId:
							maxLayerId = x[1]					
					
					if layer["layer_id"] < minLayerId:
						for x in layers_generated:
							if x[1] == minLayerId:
								layer_file_to_load = os.path.join(output_field, "static_layers_%s_%i.png" % (camera, x[0]))
								break
					elif layer["layer_id"] > maxLayerId:
						for x in layers_generated:
							if x[1] == maxLayerId:
								layer_file_to_load = os.path.join(output_field, "static_layers_%s_%i.png" % (camera, x[0]))	
								break
					else:
						maxLayerUsed = 0
						for x in layers_generated:
							if layer["layer_id"] < x[1]  and x[1] > maxLayerUsed:
								layer_file_to_load = os.path.join(output_field, "static_layers_%s_%i.png" % (camera, x[0]))
								maxLayerUsed = x[1]
							elif layer["layer_id"] < x[1]  and x[1] < maxLayerUsed:
								print("weird order ?", field_id)


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
