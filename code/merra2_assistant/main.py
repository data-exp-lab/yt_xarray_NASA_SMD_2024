import xarray as xr
import yt_xarray
import yt
from yt_xarray import transformations as tf
import numpy as np
from typing import Optional, Union
import unyt
import os
import cartopy
from dask import delayed, compute
from yt.visualization.volume_rendering.render_source import LineSource
import shapely

class ScaledGC(tf.GeocentricCartesian):
    def __init__(self,
                 radial_type: str = "radius",
                 radial_axis: Optional[str] = None,
                 r_o: Optional[Union[float, unyt.unyt_quantity]] = None,
                 coord_aliases: Optional[dict] = None,
                 use_neg_lons: Optional[bool] = False,
                 radial_scale_factor: Optional[float] = 1.0,
                 ):
        self.radial_scale_factor = radial_scale_factor
        if coord_aliases is None:
            coord_aliases = {}
        coord_aliases['lat'] = 'latitude'
        coord_aliases['lon'] = 'longitude'
        super().__init__(radial_type=radial_type, radial_axis=radial_axis,
                         r_o=r_o, coord_aliases=coord_aliases, use_neg_lons=use_neg_lons)

        self._radial_axis_id = None
        for id, c in enumerate(self.native_coords):
            if c == self.radial_axis:
                self._radial_axis_id = id
        if self._radial_axis_id is None:
            raise RuntimeError("Could not identify radial axis id")

    def _calculate_transformed(self, **coords):
        coords[self.radial_axis] = coords[self.radial_axis] * self.radial_scale_factor
        return super()._calculate_transformed(**coords)

    def _calculate_native(self, **coords):
        result = super()._calculate_native(**coords)
        new_result = [r for r in result]
        new_result[self._radial_axis_id] = new_result[self._radial_axis_id] / self.radial_scale_factor
        return tuple(new_result)


def get_subregion(dsx0, bbox_dict):
    sel_dict = {}
    for shrt, lng in zip(['lat', 'lon'], ['latitude', 'longitude']):
        val_rng = bbox_dict[lng]
        xr_da = getattr(dsx0, shrt)
        good_vals = xr_da.where(np.logical_and(xr_da >= val_rng[0], xr_da <= val_rng[1]), drop=True)
        sel_dict[shrt] = good_vals

    ds_sub_region = dsx0.sel(sel_dict)
    return ds_sub_region
def add_horizontal_mean(dsx0, bbox_dict):

    ds_sub_region = get_subregion(dsx0, bbox_dict)

    for op in ('mean', 'max', 'min'):
        func_handle = getattr(ds_sub_region.QV, op)
        QV_val = func_handle(dim=['lat', 'lon']).to_numpy()
        QV_val = np.repeat(QV_val[:, np.newaxis], dsx0.lat.size, axis=1)
        QV_val = np.repeat(QV_val[:, :, np.newaxis], dsx0.lon.size, axis=2)
        da = xr.DataArray(QV_val, dims=('lev', 'lat', 'lon'))
        dsx0[f"QV_{op}"] = da

def attach_altitude_dep_vars(dsx0: xr.Dataset, fields: tuple =None):
    # for 3D rendering, going to take the mean height at each level as
    # the altitude and add variables with altitude as dimension
    # instead of level.
    if fields is None:
        fields = ('QV', 'T', 'QV_mean', 'QV_max', 'QV_min')

    altitude = dsx0.H.mean(dim=['lat', 'lon'])
    for field in fields:
        if field in dsx0.data_vars:
            vals = xr.DataArray(dsx0.data_vars[field].to_numpy(),
                                dims=('altitude', 'lat', 'lon'),
                                coords={'altitude': altitude.to_numpy()})

            dsx0[f"{field}_by_alt"] = vals


def load_merra2_sample(time_index:int = 0, bbox_dict = None,
                       virtual_alt_scale = 10.0,
                       grid_resolution = None,
                       refine_grid=True,
                       refine_by=2,
                       refine_min_grid_size=16,
                       refine_max_iters=2000,
                       fill_value=np.nan
                       ):

    if bbox_dict is None:
        bbox_dict = {'latitude': [-1., 1.],
                     'longitude': [-90., -88.],
                     'altitude': [0., 70 * 1e3]}

    dsx = yt_xarray.open_dataset("sample_nc/MERRA2_100.inst3_3d_asm_Np.19800120.nc4")
    dsx0 = dsx.isel({'time':time_index})
    add_horizontal_mean(dsx0, bbox_dict=bbox_dict)

    fields = ('T', 'H', 'U', 'V', 'QV', 'QV_max', 'QV_min', 'QV_mean', 'RH')
    fields_for_yt = tuple([f"{fld}_by_alt" for fld in fields])
    attach_altitude_dep_vars(dsx0, fields=fields)

    ro = 6371*1e3

    gc = ScaledGC(radial_type='altitude',
                  r_o = ro,
                  use_neg_lons=True,
                  radial_scale_factor=virtual_alt_scale)

    if grid_resolution is None:
        grid_resolution = (128, 128, 128)

    ds_yt = tf.build_interpolated_cartesian_ds(
        dsx0,
        gc,
        fields=fields_for_yt,
        bbox_dict=bbox_dict,
        grid_resolution=grid_resolution,
        interp_method='nearest',
        refine_grid=refine_grid,
        refine_by=refine_by,
        refine_min_grid_size=refine_min_grid_size,
        refine_max_iters = refine_max_iters,
        fill_value=fill_value,
    )

    add_extra_fields(ds_yt)

    return dsx0, ds_yt, gc

def add_extra_fields(ds_yt):
    def _QV_for_proj(field, data):
        QV = data['stream', 'QV_by_alt']
        QV_clean = QV.copy()
        QV_clean[np.isnan(QV_clean)] = 0.0
        return QV_clean

    ds_yt.add_field(
        name=("stream", "QV_n"),
        function=_QV_for_proj,
        sampling_type="cell",
        units="",
    )

    def _dQV(field, data):
        rng = data['stream', 'QV_max_by_alt'] - data['stream', 'QV_min_by_alt']
        QV_n = data['stream', 'QV_n']

        dQV_n = QV_n - data['stream', 'QV_min_by_alt']

        dQV_n[rng>0] = dQV_n[rng>0] / rng[rng>0]
        dQV_n[np.isnan(dQV_n)] = 0.0
        dQV_n[dQV_n<0] = 0.0


        return dQV_n

    ds_yt.add_field(
        name=("stream", "dQV_n"),
        function=_dQV,
        sampling_type="cell",
        units="",
    )

    def _RH_for_proj(field, data):
        RH = data['stream', 'RH_by_alt']
        RH[np.isnan(RH)] = 0.0
        RH[RH==0.0] = 1e-12
        return RH

    ds_yt.add_field(
        name=("stream", "RH_filtered"),
        function=_RH_for_proj,
        sampling_type="cell",
        units="",
    )


def create_dQV_vr(ds_yt, with_rots=True):
    fld = ('stream', 'dQV_n')
    sc = yt.create_scene(ds_yt, lens_type="perspective", field=fld)

    source = sc[0]

    source.set_field(fld)
    source.set_log(False)

    bounds = (0, 1.0)

    # Since this rendering is done in log space, the transfer function needs
    # to be specified in log space.
    tf = yt.ColorTransferFunction(bounds)

    tf.sample_colormap(.6, w=0.0005, colormap="cmyt.arbre")
    tf.sample_colormap(.4, w=0.0005, colormap="cmyt.arbre")
    tf.sample_colormap(.9, w=0.0005, colormap="cmyt.arbre")

    source.tfh.tf = tf
    source.tfh.bounds = bounds

    source.tfh.plot("volume_rendering_images/transfer_function.png", profile_field=('index', 'ones'))

    sc.camera.north_vector = ds_yt.domain_center.d
    sc.camera.set_focus(sc.camera.focus)
    sc.camera.zoom(0.6)

    sc.save("volume_rendering_images/rendering0000.png", sigma_clip=4)

    if with_rots:
        yt.set_log_level(50)
        nframes = 100
        total_rot = 360
        drot = total_rot / nframes
        for irlot in range(nframes):
            sc.camera.rotate(drot * np.pi / 180, rot_center=sc.camera.focus)
            sc.save(f"volume_rendering_images/rendering{str(irlot + 1).zfill(4)}.png", sigma_clip=4)

def create_RH_vr(ds_yt, gc:ScaledGC, nframes=100, save_dir=None, skip_render=False):

    if save_dir is None:
        save_dir = "volume_rendering_images"
    if os.path.isdir(save_dir) is False:
        os.mkdir(save_dir)

    fld = ('stream', 'RH_filtered')
    cmap = "cmyt.arbre"

    lnsrc = build_state_line_sources(gc)

    sc = yt.create_scene(ds_yt,  field=fld)

    source = sc[0]
    source.set_field(fld)
    source.set_log(True)

    bounds = (1e-6, 1)

    # Since this rendering is done in log space, the transfer function needs
    # to be specified in log space.
    tf = yt.ColorTransferFunction(np.log10(bounds))
    for n_exp in range(-5,0):
        tf.sample_colormap(float(n_exp), w=0.01, colormap=cmap)

    tf.sample_colormap(np.log10(.95), w=0.01, colormap=cmap)

    source.tfh.tf = tf
    source.tfh.bounds = bounds

    tf_file = os.path.join(save_dir, "transfer_function.png")
    source.tfh.plot(tf_file, profile_field=('index', 'ones'))

    sc.camera.north_vector = ds_yt.domain_center.d
    sc.camera.set_focus(sc.camera.focus)
    sc.camera.zoom(1.5)

    sc.add_source(lnsrc)

    drot = 360./20. * 11.
    sc.camera.rotate(drot * np.pi / 180, rot_center=ds_yt.domain_center)

    if skip_render:
        return sc

    vr_file = os.path.join(save_dir, "RH_rendering_0000.png")
    sc.save(vr_file, sigma_clip=3.5)
    nframes = int(nframes)
    if nframes > 0:
        yt.set_log_level(50)
        total_rot = 360
        drot = total_rot / nframes
        for irlot in range(nframes):
            sc.camera.rotate(drot * np.pi / 180, rot_center=ds_yt.domain_center)
            vr_file = os.path.join(save_dir, f"RH_rendering_{str(irlot + 1).zfill(4)}.png")
            sc.save(vr_file, sigma_clip=4)


def build_state_line_sources(gc: tf.Transformer):
    state_segs = []
    for s in cartopy.feature.STATES.geometries():
        state_segs.append(delayed(process_state)(s, gc))

    state_segs = np.concatenate(compute(*state_segs))
    colors = np.ones((state_segs.shape[0], 4))
    colors[:, 3] = 0.1
    lsrc = LineSource(state_segs, colors=colors)
    return lsrc
def transform_geom_bounds(linesegs, xy, gc: ScaledGC):
    lons = np.array(xy[0])
    lons[lons>180] = lons[lons>180] - 360.
    lats = np.array(xy[1])

    coords = {'latitude': lats, 'longitude': lons, gc.radial_axis: 0.0}
    x, y, z = gc.to_transformed(**coords)

    for iseg in range(len(x) - 1):
        lineseg = [[x[iseg], y[iseg], z[iseg]], [x[iseg + 1], y[iseg + 1], z[iseg + 1]]]
        linesegs.append(lineseg)
    return linesegs


def process_state(state, gc):
    linesegs = []
    if isinstance(state, shapely.geometry.polygon.Polygon):
        geoms_iter = [state,]
    elif isinstance(state, shapely.geometry.multipolygon.MultiPolygon):
        geoms_iter = state.geoms
    else:
        msg = f"Unexpected geometry type: {type(state)}"
        raise TypeError(msg)

    for geom in geoms_iter:
         linesegs = transform_geom_bounds(linesegs, geom.boundary.xy, gc)
    return linesegs