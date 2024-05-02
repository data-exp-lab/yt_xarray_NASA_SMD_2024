import yt_idv
from merra2_assistant.main import load_merra2_sample

bbox_dict = {'altitude':[0, 68*1e3], 
             'latitude': [25, 75],
             'longitude': [-150., -100.]}
dsx0, ds_yt = load_merra2_sample(bbox_dict=bbox_dict, 
                                 virtual_alt_scale=10., 
                                 grid_resolution = (16,)*3,
                                 refine_max_iters=2000,
                                 refine_min_grid_size=4,
                                 refine_by=8,
                                 fill_value = 1e-12)

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds_yt, "RH_filtered", no_ghost=True)
rc.run()