import os
import glob
import cv2
import shutil
import json
from multiprocessing import Process, Pool, Manager
import numpy as np

dir_path = os.path.dirname(os.path.realpath(__file__))

# Number of threads to use
NUM_THREADS = 12

# directory where the TIFF files for the PC background are located.
PC_FOLDER = os.path.join(dir_path, "PC_Extracted_Fields_Background")

# directory where the TIFF files for the PSX background are located.
PSX_FOLDER = os.path.join(dir_path, "PSX_Extracted_Fields_Background")


PSX_INFO_LIST = sorted(glob.glob(PSX_FOLDER+"\\CD_*\\*.info"))
PC_INFO_LIST = sorted(glob.glob(PC_FOLDER+"\\*.info"))
pc_infos = dict()

file_matching = dict()



FileCheck = False

def extract_pc_infos(pc_info):
	tmp_pc_infos = dict()
	with open(pc_info) as f:
			tile_PC = int(f.readline())
			info_PC = f.readlines()
			if not tile_PC in tmp_pc_infos:
				tmp_pc_infos[tile_PC] = dict()
			for i in range(0, len(info_PC)):

				layer = dict()
				infos_layer = info_PC[i].strip().split(" ")
				layer_blend = int(infos_layer[7])
				layer_number = infos_layer[0]
				layer_camera = int(infos_layer[1])

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

				if not layer_camera in tmp_pc_infos[tile_PC]:
					tmp_pc_infos[tile_PC][layer_camera]  = dict()
					tmp_pc_infos[tile_PC][layer_camera]["layers"] =[]
					img_PC_source = pc_info.replace(".info", "")
					tmp_pc_infos[tile_PC][layer_camera]["img"] = img_PC_source
					img_pc = cv2.imread(filename = img_PC_source, flags = cv2.IMREAD_UNCHANGED )
					tmp_pc_infos[tile_PC][layer_camera]["width"] = img_pc.shape[0]
					tmp_pc_infos[tile_PC][layer_camera]["height"] = img_pc.shape[1]
					tmp_pc_infos[tile_PC][layer_camera]["size"] = os.path.getsize(img_PC_source)

				tmp_pc_infos[tile_PC][layer_camera]["layers"].append(layer)

	
	return tmp_pc_infos


def match_PC_PSX(pc_info_files):
	for info_file in pc_info_files:
		pass

def check_duplicate(img_duplicates):
	key, value = img_duplicates
	
	dups = {}

	if len(value["duplicate"]) != 0 :
		tile_PC = value["field"]

		debug = False
		if value["img"] == r"D:\FFIX_HD_MOD\PC_Extracted_Fields_Background\PC_16_4.tiff":
			print("Debug", value["img"])
			debug = True
		# we are reading all the layers
		ret, layers_PC = cv2.imreadmulti(filename = value["img"], flags = cv2.IMREAD_UNCHANGED )
		
		for dup in value["duplicate"]:
			# And all the layers of potential duplicates
			sameFile = True
			ret, layers_dup_PC = cv2.imreadmulti(filename = dup, flags = cv2.IMREAD_UNCHANGED )

			# for some reasons, black images are messing with cv2....
			if len(layers_PC) == 1:
				layer_r, layer_g, layer_b, layer_a = cv2.split(layers_PC[0])
				if cv2.countNonZero(layer_b) == 0 or cv2.countNonZero(layer_g) == 0 or cv2.countNonZero(layer_r) == 0:
					sameFile = False

				layer_r, layer_g, layer_b, layer_a = cv2.split(layers_dup_PC[0])

				if cv2.countNonZero(layer_b) == 0 or cv2.countNonZero(layer_g) == 0 or cv2.countNonZero(layer_r) == 0:
				 	sameFile = False

			if sameFile == True:
				for i in range(0, len(layers_PC)):

					difference = cv2.subtract(layers_PC[i], layers_dup_PC[i])
					r, g, b, a = cv2.split(difference)

					# If layer A - layer B = 0, there is absolutely no difference in that layer.
					# If there is a difference, it's not the same file, no need to check further !
					if cv2.countNonZero(b) != 0 or cv2.countNonZero(g) != 0 or cv2.countNonZero(r) != 0:
						sameFile = False
						break

			if sameFile == True:
				if not value["img"] in dups :
					dups[value["img"]] = []
				dups[value["img"]].append(dup)
			else :
				# we know that this layer is not the same than our key, but it can be identical to any other layer !
				# We do the same test - Should be a function to avoid duplicating code, but I'm lazy.
				# Feel free to make it nicer :)
				for other_dup in value["duplicate"]:
					if other_dup != dup and other_dup not in dups.keys():
						for current_dups in dups :
							if other_dup in dups[current_dups]:
								continue

						other_sameFile = True


						ret, other_layer_dup_PC = cv2.imreadmulti(filename = other_dup, flags = cv2.IMREAD_UNCHANGED )

						if len(other_layer_dup_PC) == 1:
							layer_r, layer_g, layer_b, layer_a = cv2.split(other_layer_dup_PC[0])
							if cv2.countNonZero(layer_b) == 0 or cv2.countNonZero(layer_g) == 0 or cv2.countNonZero(layer_r) == 0:
								other_sameFile = False

							layer_r, layer_g, layer_b, layer_a = cv2.split(layers_dup_PC[0])

							if cv2.countNonZero(layer_b) == 0 or cv2.countNonZero(layer_g) == 0 or cv2.countNonZero(layer_r) == 0:
							 	other_sameFile = False

						if other_sameFile == True:
							for i in range(0, len(layers_dup_PC)):
								difference = cv2.subtract(layers_dup_PC[i], other_layer_dup_PC[i])
								b, g, r, a = cv2.split(difference)
								if cv2.countNonZero(b) != 0 or cv2.countNonZero(g) != 0 or cv2.countNonZero(r) != 0:
									other_sameFile = False
									break
							if other_sameFile == True:
								if not dup in dups :
									dups[dup] = []
								dups[dup].append(other_dup)

				

	return dups
					
        	
def check_duplicate_main(orig_info_list, save_json):

	pool = Pool(NUM_THREADS)

	pc_infos = dict()
	tmp_result = pool.map(extract_pc_infos, orig_info_list)
	for result in tmp_result:
		for tile_PC in result:
			if not tile_PC in pc_infos:
				pc_infos[tile_PC] = result[tile_PC]
			
			else:
				for camera in result[tile_PC]:
					if not camera in pc_infos[tile_PC]:
						pc_infos[tile_PC][camera] = result[tile_PC][camera]
					else:
						pass
	# search for duplicate fields.
	i = 0
	img_duplicates = dict()


	# Simple check here : If the size are equal, and they have the same layers, we can assume the files are the same.

	for tile_PC in pc_infos:
		tile_info = pc_infos[tile_PC]
		
		for camera in tile_info:
			camera_info = tile_info[camera]

			img = camera_info["img"]
			size_img = camera_info["size"]
			width, height = (camera_info["width"], camera_info["height"])
			key = ("%i_%i_%i_%i" %(size_img, width, height, len(camera_info["layers"])))
			if not key in img_duplicates:
				img_duplicates[key] = dict()
				img_duplicates[key]["field"] = tile_PC
				img_duplicates[key]["img"] = img
				img_duplicates[key]["duplicate"] = []

			else:
				img_duplicates[key]["duplicate"].append(img)
			i = i + 1


	with open("Unique_Fields_PC_Unfiltered.json", "w") as write_file:
		json.dump(pc_infos, write_file, indent=4)
	
	print("Before filtering", len(pc_infos))

	# More complicated check
	dups = pool.map(check_duplicate, img_duplicates.items())
	
	with open("Duplicated_PC_Images.json", "w") as write_file:
		json.dump(dups, write_file, indent=4)

	for dup in dups:
		if len(dup) != 0:
			for original in dup:
				duplicates = dup[original]
				for duplicate in duplicates:
					tilesToDelete = []
					for tile_PC in pc_infos:
						camerasToDelete = []
						tile_info = pc_infos[tile_PC]

						for camera in tile_info:
							camera_info = tile_info[camera]
							if duplicate == camera_info["img"] :
								camerasToDelete.append(camera)

						for cameraToDelete in camerasToDelete:
							if pc_infos[tile_PC].pop(cameraToDelete, None) == None:
								print("Error")
							else:
								if len(pc_infos[tile_PC]) == 0:
									tilesToDelete.append(tile_PC)
					for tileToDelete in tilesToDelete:
						if pc_infos.pop(tileToDelete, None) == None:
							print("Error")

	print("After filtering", len(pc_infos))

	with open(save_json, "w") as write_file:
		json.dump(pc_infos, write_file, indent=4)

	return pc_infos


def match_psx_pc(fields, pc_infos, psx_infos, return_dict):

	for field in fields:
		
		
		field_info = pc_infos[field]

		cam_result = dict()

		if len(field_info) == 0:
			print("No camera for field", field)

		for camera in field_info:
			camera_info = field_info[camera]
			layers = camera_info["layers"]
			img_pc = camera_info["img"]
			num_layers = len(layers)

			potential_matchs = []

			num_no_text_layers = 0

			for layer in layers:
				if layer["is_static"] and layer["distance"] < 5:
					break
				# special case, manual correction.
				if field == "1201" and layer["layer_number"] == 26:
					break

				num_no_text_layers = num_no_text_layers + 1

			for psx_field in psx_infos:
				psx_field_info = psx_infos[psx_field]
				if not camera in psx_field_info:
					continue
				
				psx_camera_info = psx_field_info[camera]
				psx_layers = psx_camera_info["layers"]
				img_psx = psx_camera_info["img"]
				psx_num_layers = len(psx_layers)


				if psx_num_layers < num_no_text_layers:
					# not worth investigating this.
					continue

				num_match = 0

				for psx_layer in psx_layers:			
					
					for layer in layers:
						if layer["is_static"] and layer["distance"] < 5:
							continue

						if ( 
						psx_layer["layer_id"]  == layer["layer_id"] and
						psx_layer["camera_id"] == layer["camera_id"] and
						psx_layer["blend"] == layer["blend"] and
						psx_layer["tile_amount"] == layer["tile_amount"] and
						psx_layer["distance"] == layer["distance"] and
						psx_layer["has_parallax"] == layer["has_parallax"] and
						psx_layer["is_static"] == layer["is_static"] and
						psx_layer["is_attached"] == layer["is_attached"] and
						psx_layer["is_first_of_anim"] == layer["is_first_of_anim"] and
						psx_layer["is_looping"] == layer["is_looping"] 
						) :
							
							num_match = num_match + 1



				if num_match >= num_no_text_layers:
					potential_matchs.append(psx_field)


			if len(potential_matchs) == 0:
				print("No match found for", img_pc, "camera", camera )
				 

			if len(potential_matchs) > 1:

				if(os.path.exists(img_pc) == False):
					print("Path", img_pc, "is not found")

				ret, layers_PC = cv2.imreadmulti(filename = img_pc, flags = cv2.IMREAD_UNCHANGED )

				betterField = - 1
				minMean = 10000000000000000000


				for potential_field in potential_matchs:
					meanImg = 0
					
					if(os.path.exists(psx_infos[potential_field][camera]["img"]) == False):
						print("Path", psx_infos[potential_field][camera]["img"], "is not found")



					ret, layers_PSX = cv2.imreadmulti(filename = psx_infos[potential_field][camera]["img"], flags = cv2.IMREAD_UNCHANGED )
					for i in range(0, len(layers_PC)):
						
						layer_psx = cv2.resize(layers_PSX[i], (0,0), fx=2.0, fy=2.0, interpolation = cv2.INTER_NEAREST) 
						difference = cv2.subtract(layers_PC[i], layer_psx)
						meanDiff = cv2.mean(difference)
						meanImg = meanImg +( meanDiff[0] + meanDiff[1] + meanDiff[2])
						
					if(meanImg < minMean):
						betterField = potential_field
						minMean = meanImg



				potential_matchs.clear()
				potential_matchs=[betterField]


			cam_result[camera] = potential_matchs[0]

		return_dict[field] = cam_result


def chunks(l, n):
    n = max(1, n)
    return (l[i:i+n] for i in range(0, len(l), n))

if __name__ == '__main__':

	if os.path.exists("Unique_Fields_PC.json") == False:
		pc_infos = check_duplicate_main(PC_INFO_LIST, "Unique_Fields_PC.json")
	else:
		with open("Unique_Fields_PC.json", "r") as read_file:
			pc_infos = json.load(read_file)		

	if os.path.exists("Unique_Fields_PSX.json") == False:
		psx_infos = check_duplicate_main(PSX_INFO_LIST, "Unique_Fields_PSX.json")		
	else:
		with open("Unique_Fields_PSX.json", "r") as read_file:
			psx_infos = json.load(read_file)

	
	#now, we are trying match PC with PSX images !
	
	fields_list = list(pc_infos.keys())
	
	split = np.array_split(fields_list, NUM_THREADS)

	manager = Manager()
	return_dict = manager.dict()	
	
	processes = []
	
	for fields in split:
		p = Process(target=match_psx_pc, args=(fields, pc_infos, psx_infos, return_dict))
		processes.append(p)

	for process in processes:
		process.start()

	for process in processes:
		process.join()

	# save all the infos in the json matching file.
	with open("match_PC_PSX.json", "w") as write_file:
		json.dump(return_dict.copy(), write_file, indent=4)




									


		


