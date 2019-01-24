1. In Hades Workshop 
Export backgrounds for the PC & all ISO of the PSX version to the right folders (one folder named CD_x per CD for the PSX)
You need to export through the Batch menu with these settings :
- Merge Tilesets : OFF
- Sort Tilesets by Depth : ON
- All titles (you need to deselect the field with "FMV" in the name around "Castle" or it will crash.)

Call the file name "PC" for PC version, and PSX for "PSX" version.


2. OPTIONAL STEP
You can run 0-export_all_layers_for_check.py. That will extract all the layers from the PC version. 
At the end of the '5-Prepare_for_Hades.py", your upscaled folder should have exactly the same structure & number of layers than the folder created by this script.

From this step, everything step will take a while to process. 

3. Run 1-match_pc_psx.py

Will check duplicate fields and export all the necessary layers infos

You should end up with three files:
	- match_PC_PSX.json
	- Unique_Fields_PSX.json
	- Unique_Fields_PC.json


4. Run 2-sorting_files_and_extract_layers.py

You should end up with two folders:
	- Extracted_Fields_Layers
	- Extracted_Fields_Alpha_Layers
	
In Extracted_Fields_Alpha_Layers you should have all the FieldXX folder, and one tiff per layer containing the alpha of the PC version.
In Extracted_Fields_Layers you should have all the FieldXX folder, and one tiff per layer containing the color of the PSX (preferably) or PC version.	
	
5. Run 3-prepare_layers_for_upscale.py	

You will end up with a folder named : Combined_Fields_Layers
In that folder, you will see each field as a directory.
Inside a field, you will have static layers & anim layers.

5. OPTIONAL BUT RECOMMANDED STEP
Save Combined_Fields_Layers for backup. Run a denoiser on all the images in that folder (ie. Photoshop batch script, Waifu 2x, ...)
The recommanded process is : Resize the image 4.0x (no interpolation), run the denoiser, and shrink back the image 0.25x. 


6. Run 4-Upscale.py
This will run the actual upscaling. result folder in Upscaled_Fields_Layers.
Alternatively, you can use Gigapixel or Waifu2X, as your convenience. The ending folder must be the same !

7. Run 5-Prepare_for_Hades.py
The output folder will be Upscaled_Fields_Layers.
This will split back all the layers so Hades Workshop recognize them.


8. OPTIONAL STEP
Run 6-check_layers.py. This will check the upscale layer against the original folder created at step 2. If they are the same, everything is fine for Hades !

9. Mass convert Upscaled_Fields_Layers to .TEX files + Mass import files in Hades. 
Reverse Order = Off !
Script field = On !
Don't forget to change the image size to 64 & patch the game accordingly.

10. Enjoy !

