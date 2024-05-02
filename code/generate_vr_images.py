from merra2_assistant.main import load_merra2_sample, create_RH_vr

bbox_dict = {'altitude':[0, 68*1e3],
             'latitude': [25, 75],
             'longitude': [-150., -100.]}
dsx0, ds_yt, gc = load_merra2_sample(bbox_dict=bbox_dict,
                                 virtual_alt_scale=20.,
                                 grid_resolution = (16,)*3,
                                 refine_max_iters=2000,
                                 refine_min_grid_size=2,
                                 refine_by=8,
                                 fill_value = 0.0)

create_RH_vr(ds_yt, gc, nframes=50)
