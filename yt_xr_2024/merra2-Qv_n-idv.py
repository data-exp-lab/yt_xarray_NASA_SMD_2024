import yt_idv
from merra2_assistant.main import load_merra2_sample

dsx0, ds_yt = load_merra2_sample()

rc = yt_idv.render_context(height=800, width=800, gui=True)
sg = rc.add_scene(ds_yt, "dQV_pos", no_ghost=True)
rc.run()