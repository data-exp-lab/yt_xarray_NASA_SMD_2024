# this script copies the relevant figures over to the jupyter book directory
from shutil import copyfile
from os.path import join 

if __name__ == "__main__":
    files_to_copy = [join('slice_images','combo_merra2_interp_slices.png'),
                     join('volume_rendering_images','RH_rendering_0000_annotated.png'),
                     join('slice_images','w_us_tomography.png'),
                     join('slice_images','w_us_tomography_carto_100km.png'),               
                     join('volume_rendering_images','wus_tomo_annotated.png'),
                     join('slice_images','merra2_from_yt_convenience_800_hpa.png'),
                     join('slice_images','merra2_subset_from_load_grid_800hpa.png'),
                     join('slice_images','merra2_phase_plot.png')                 
                    ]
    dest_folder = os.path.join('..','yt_xr_2024','_static', 'images')
    
    for fi in files_to_copy:
        dest_fi = os.path.join(dest_folder, os.path.basename(fi))
        copyfile(fi, dest_fi)
