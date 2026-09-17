#!/usr/bin/env python3
"""
Generate the colormapped PNGs of the hero comparison slider: standard DIC (left)
against Argos2D (right), where the Argos2D side is the neural correlation result
(xR-DIC).

Source: the Argos2D exports of Data_Stinville (Stinville et al., Scientific Data
9, 2022, 460), sub-folders DIC and XR_DIC, pair step1_E1_Ti6_P4_4.

Fields:
    - displacement -> uy, jet, shared p1-p99 scale
    - strain       -> EFFECTIVE STRAIN (Stinville), viridis, 0-10 %

    eps_eff = sqrt( (0.5 (du/dx - dv/dy))^2 + (0.5 (du/dy + dv/dx))^2 )

The strain is computed HERE from the exported displacements, identically for
both sides, with the same least-squares derivative (half-width 3) and the same
0-10 % scale as the neural-correlation section of the page
(OmniCorr2D/scripts/doc_figures/make_hdic_xrdic_slider.py). Both sliders are
therefore directly comparable.

GRIDS. The DIC run uses a 5 px spacing, the neural run a 1 px one. Derivatives
are taken on each field's own grid (divided by its spacing), then the DIC maps
are resampled bilinearly onto the neural pixel grid. For the same ROI, the first
DIC point sits 60 px inside the ROI (half-window 30 + search 30) and the first
neural pixel 62 px (seed window 65), hence the 2 px offset below.

Usage:
    python make_field_screens.py
"""
from pathlib import Path

import numpy as np
import tifffile
from matplotlib import colormaps
from matplotlib.colors import Normalize
from PIL import Image
from scipy.ndimage import correlate1d, map_coordinates

SRC = Path(r"C:\Users\Samue\Documents\OmniCorr\Data_Stinville")
DEST = Path(__file__).resolve().parent / "screens"
STEM = "step1_E1_Ti6_P4_4"

DIC_STEP = 5
DIC_BORDER = 60      # half-window 30 + search 30
XR_BORDER = 62       # half seed window 32 + search 30
STRAIN_KERNEL = 3
STRAIN_VMAX_PCT = 10.0
DISP_PCT = (1, 99)



def load(folder, comp):
    return tifffile.imread(SRC / folder / "Displacements" / f"{STEM}_{comp}.tif").astype(np.float64)


def deriv(f, axis, spacing):
    k = np.arange(-STRAIN_KERNEL, STRAIN_KERNEL + 1, dtype=np.float64)
    return correlate1d(f, k / (k ** 2).sum(), axis=axis, mode="nearest") / spacing


def effective_strain(u, v, spacing):
    du_dy, du_dx = deriv(u, 0, spacing), deriv(u, 1, spacing)
    dv_dy, dv_dx = deriv(v, 0, spacing), deriv(v, 1, spacing)
    return np.sqrt((0.5 * (du_dx - dv_dy)) ** 2 + (0.5 * (du_dy + dv_dx)) ** 2)


def dic_to_pixels(grid, shape):
    """Bilinear resampling of a DIC grid onto the neural pixel grid."""
    h, w = shape
    off = (XR_BORDER - DIC_BORDER) / DIC_STEP
    yy, xx = np.meshgrid(np.arange(h) / DIC_STEP + off, np.arange(w) / DIC_STEP + off, indexing="ij")
    return map_coordinates(grid, [yy, xx], order=1, mode="nearest")


def save(data, norm, cmap_name, name):
    cmap = colormaps[cmap_name].with_extremes(bad=(1, 1, 1, 1))
    rgb = (cmap(norm(data))[..., :3] * 255).astype(np.uint8)
    out = DEST / name
    Image.fromarray(rgb, "RGB").save(out, optimize=True)
    print(f"   -> screens/{name}  ({data.shape[1]}x{data.shape[0]})")


def main():
    xr_u, xr_v = load("XR_DIC", "ux"), load("XR_DIC", "uy")
    dic_u, dic_v = load("DIC", "ux"), load("DIC", "uy")
    shape = xr_u.shape

    # Displacement uy, shared percentile scale
    dic_uy = dic_to_pixels(dic_v, shape)
    stack = np.concatenate([a[np.isfinite(a)] for a in (dic_uy, xr_v)])
    lo, hi = np.percentile(stack, DISP_PCT)
    print(f"[displacement uy] jet {lo:.4g} .. {hi:.4g}")
    norm = Normalize(vmin=lo, vmax=hi, clip=True)
    save(dic_uy, norm, "jet", "displacement_DIC.png")
    save(xr_v, norm, "jet", "displacement_Argos2D.png")

    # Effective strain, fixed 0-10 % scale
    dic_eps = dic_to_pixels(effective_strain(dic_u, dic_v, DIC_STEP), shape) * 100.0
    xr_eps = effective_strain(xr_u, xr_v, 1) * 100.0
    print(f"[effective strain] viridis 0 .. {STRAIN_VMAX_PCT} %")
    norm = Normalize(vmin=0.0, vmax=STRAIN_VMAX_PCT, clip=True)
    save(dic_eps, norm, "viridis", "strain_DIC.png")
    save(xr_eps, norm, "viridis", "strain_Argos2D.png")


if __name__ == "__main__":
    main()
