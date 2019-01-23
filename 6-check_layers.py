import os
import glob
import cv2
import shutil
import json
dir_path = os.path.dirname(os.path.realpath(__file__))

REF_FOLDER = os.path.join(dir_path, "PC_LAYERS_FOR_CHECKING")
UP_FOLDER = os.path.join(dir_path, "Upscaled_Fields_Layers")


field_ref_list = sorted(glob.glob(REF_FOLDER+"\\Field*"))


for field in field_ref_list:
	field_dir = os.path.basename(field)

	field_dir_upscaled = os.path.join(UP_FOLDER, field_dir)

	if os.path.exists(field_dir_upscaled) == False:
		continue

	img_ref_list = sorted(glob.glob(field+"\\*.tiff"))	
	for img_ref in img_ref_list:
		upscaled_path = os.path.join(field_dir_upscaled, os.path.basename(img_ref))
		if os.path.exists(upscaled_path) == False:
			print("Can't find", upscaled_path)

	