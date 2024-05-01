import xarray as xr
import yt_xarray
import yt
from yt_xarray import transformations as tf
from scipy.spatial import cKDTree
import numpy as np

class KdTreeContainer:

    def __init__(self, dsx0):
        self.full_shape = dsx0.H.shape

        lons1d = dsx0.lon.to_numpy()
        lons = np.repeat(lons1d[:, np.newaxis], dsx0.lat.size, axis=1)
        lons = np.repeat(lons[:, :, np.newaxis], dsx0.lev.size, axis=2)
        lons = np.transpose(lons).ravel()

        lats1d = dsx0.lat.to_numpy()
        lats = np.repeat(lats1d[np.newaxis, :], dsx0.lon.size, axis=0)
        lats = np.repeat(lats[:, :, np.newaxis], dsx0.lev.size, axis=2)
        lats = np.transpose(lats).ravel()

        heights = dsx0.H.to_numpy().ravel()
        self.ids = np.arange(heights.size)
        self.finite_mask = np.isfinite(heights)
        self.finite_ids = self.ids[self.finite_mask]


        heights_n = self._get_normalized(heights[self.finite_mask], 'height')
        lats_n = self._get_normalized(lats[self.finite_mask], 'lat')
        lons_n = self._get_normalized(lons[self.finite_mask], 'lon')

        self.tree = cKDTree(np.column_stack([heights_n, lats_n, lons_n]))

    def _get_normalized(self, vals, dim: str):
        return vals

def add_horizontal_mean(dsx0):

    for op in ('mean', 'max', 'min'):
        func_handle = getattr(dsx0.QV, op)
        QV_val = func_handle(dim=['lat', 'lon']).to_numpy()
        QV_val = np.repeat(QV_val[:, np.newaxis], dsx0.lat.size, axis=1)
        QV_val = np.repeat(QV_val[:, :, np.newaxis], dsx0.lon.size, axis=2)
        da = xr.DataArray(QV_val, dims=('lev', 'lat', 'lon'))
        dsx0[f"QV_{op}"] = da



def load_merra2_sample(time_index:int = 0, bbox_dict = None,
                       virtual_alt_scale = 10.0,
                       grid_resolution = None):
    dsx = yt_xarray.open_dataset("sample_nc/MERRA2_100.inst3_3d_asm_Np.19800120.nc4")
    dsx0 = dsx.isel({'time':time_index})
    add_horizontal_mean(dsx0)

    ro = 6371*1e3
    gc = tf.GeocentricCartesian(radial_type='altitude',
                                r_o=ro,
                                use_neg_lons=True, )

    kdTree_holder = KdTreeContainer(dsx0)
    def interp_at_height(data: xr.DataArray, coords):
        v_alt = coords[0]
        height = v_alt / virtual_alt_scale
        # print(height.max())
        # print(height.min())
        lat = coords[1]
        lon = coords[2]

        sample_points = np.column_stack([height, lat, lon])
        d, sub_ids = kdTree_holder.tree.query(sample_points, k=1)
        full_ids = kdTree_holder.finite_ids[sub_ids]

        lev_id, lat_id, lon_id = np.unravel_index(full_ids, kdTree_holder.full_shape)

        lev_id = xr.DataArray(lev_id, dims='points')
        lat_id = xr.DataArray(lat_id, dims='points')
        lon_id = xr.DataArray(lon_id, dims='points')

        return data.isel({'lev': lev_id, 'lat': lat_id, 'lon': lon_id})

    if grid_resolution is None:
        grid_resolution = (128, 128, 128)
    if bbox_dict is None:
        bbox_dict = {'latitude': [-1., 1.],
                     'longitude': [-90., -88.],
                     'altitude': [0., 70 * 1e3]}

    bbox_dict['altitude'] = [bbox_dict['altitude'][0]* virtual_alt_scale,
                             bbox_dict['altitude'][1] * virtual_alt_scale
                             ]


    ds_yt = tf.build_interpolated_cartesian_ds(
        dsx0,
        gc,
        fields=('T', 'H', 'U', 'V', 'QV', 'QV_max', 'QV_min', 'QV_mean'),
        bbox_dict=bbox_dict,
        grid_resolution=grid_resolution,
        interp_method='interpolate',
        interp_func=interp_at_height,
    )

    add_extra_fields(ds_yt)

    return dsx0, ds_yt

def add_extra_fields(ds_yt):
    def _QV_for_proj(field, data):
        QV = data['stream', 'QV']
        QV_clean = QV.copy()
        QV_clean[~np.isfinite(QV_clean)] = 0.0
        return QV_clean

    ds_yt.add_field(
        name=("stream", "QV_n"),
        function=_QV_for_proj,
        sampling_type="cell",
        units="",
    )

    def _dQV(field, data):
        rng = data['stream', 'QV_max'] - data['stream', 'QV_min']
        dQV_n = (data['stream', 'QV'] - data['stream', 'QV_min'])/rng
        return dQV_n

    ds_yt.add_field(
        name=("stream", "dQV_n"),
        function=_dQV,
        sampling_type="cell",
        units="",
    )


