import os
import sys
import glob
import cv2
import shutil
import json

import numpy as np
import torch

DRY_RUN = False

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(dir_path, 'ESRGAN'))

import architecture as arch

# Path to the trained ESRGAN model.
model_path = os.path.join(dir_path, "GAN_Trained", "FF9_Trained.pth")

# The composited layers folder.
COMBINED_FIELD_FOLDER = os.path.join(dir_path, "Combined_Fields_Layers")

# Where the upscaled files will be.
UPSCALED_FIELD_FOLDER = os.path.join(dir_path, "Combined_Upscaled_Fields_Layers")

fields_list = sorted(glob.glob(COMBINED_FIELD_FOLDER +"\\Field*"))

device = torch.device('cuda')  # if you want to run on CPU, change 'cuda' -> cpu

model = arch.RRDB_Net(3, 3, 64, 23, gc=32, upscale=4, norm_type=None, act_type='leakyrelu', \
                        mode='CNA', res_scale=1, upsample_mode='upconv')

model.load_state_dict(torch.load(model_path), strict=True)
model.eval()
for k, v in model.named_parameters():
    v.requires_grad = False
model = model.to(device)


for field in fields_list :
	print(field)

	layer_list =  sorted(glob.glob(field +"\\*.png"))

	for layer in layer_list:
		field_id = os.path.basename(field)
		
		output_path = os.path.join(UPSCALED_FIELD_FOLDER, field_id)
		if not os.path.exists(output_path):
			os.makedirs(output_path)

		if DRY_RUN == False:
			if os.path.exists(os.path.join(output_path, os.path.basename(layer))):
				continue
			img = cv2.imread(layer, cv2.IMREAD_COLOR)
			
			# If the image is not at the PSX resolution for some reason (denoiser, ...), you can rescale it here.
			#img = cv2.resize(img, (0,0), fx=0.25, fy=0.25, interpolation = cv2.INTER_NEAREST) 
			img = img * 1.0 / 255
			img = torch.from_numpy(np.transpose(img[:, :, [2, 1, 0]], (2, 0, 1))).float()
			img_LR = img.unsqueeze(0)
			img_LR = img_LR.to(device)

			output = model(img_LR).data.squeeze().float().cpu().clamp_(0, 1).numpy()
			output = np.transpose(output[[2, 1, 0], :, :], (1, 2, 0))
			output = (output * 255.0).round()

			cv2.imwrite(os.path.join(output_path, os.path.basename(layer)), output)
