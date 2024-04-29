---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Recent improvements to `yt`, `yt_xarray`


**yt_xarray: yt api access**: 

initial setup: silencing unrelated warnings and logs for brevity here. 

```{code-cell}
import yt_xarray
import yt
import warnings
warnings.filterwarnings("ignore") # silence the cartopy bounds warning

yt.set_log_level(50)
yt_xarray.utilities.logging.ytxr_log.setLevel(50) 
```

load the data. data is local file, data is from the MERRA-2 reanalysis dataset (hosted at 
[GES DISC](https://disc.gsfc.nasa.gov/datasets/M2I3NPASM_5.12.4/summary), NASA EarthData) 

```{code-cell}
dsx = yt_xarray.open_dataset("sample_nc/MERRA2_100.inst3_3d_asm_Np.19800120.nc4")

dsx0 = dsx.isel({'time':0})
slc = dsx0.yt.SlicePlot('altitude', 'T', window_size=(4,2))
slc.set_log('T', False)
slc.set_zlim('T', 200, 300)

```


**yt: geoquiver**: 

```{code-cell}
ds = dsx.yt.load_grid(fields=['U', 'V'], sel_dict={'time':0}, use_callable=False)

slc = yt.SlicePlot(ds, 'altitude', 'U', window_size=(4,2))
slc.set_log('U', False)
slc.annotate_quiver('U', 'V')
slc.show()
```

**yt: cartesian cutting plane**:


