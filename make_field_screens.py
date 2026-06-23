#!/usr/bin/env python3
"""
Generate colormapped PNGs of DIC / H-DIC fields for the Argos website.

Reads the float32 TIFF field exports from the Img_Stinville dataset, applies a
colormap (jet for displacement, viridis for strain) with a *shared* color scale
within each before/after pair, and writes the PNGs into the website's screens/
directory, overwriting the current comparison-slider images.

Field choices (as requested):
    - displacement -> uy
    - strain       -> von Mises (evm)

Usage:
    python make_field_screens.py
"""
from pathlib import Path

import numpy as np
import tifffile
from matplotlib import colormaps
from matplotlib.colors import Normalize
from PIL import Image

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
SRC = Path(r"C:\Users\Samue\Documents\OmniCorr\dev_DLDIC\images\Img_Stinville")
DEST = Path(r"C:\Users\Samue\Documents\OmniCorr\Argos_website\screens")
STEM = "step1_E1_Ti6_P4_4"          # common file prefix in the dataset
SCALE = 1                           # integer upscale factor (1 = native resolution)

# Each entry produces a DIC / H-DIC pair that shares one color scale so the two
# sides of the slider are directly comparable.
#   component  : TIFF suffix to read (file is "<STEM>_<component>.tif")
#   cmap       : matplotlib colormap name
#   pct        : (low, high) percentiles used for the color limits
#   vmax_scale : multiplier on the upper limit; >1 widens the range
#                (i.e. lowers the contrast). Optional, defaults to 1.0.
#   dirs       : (standard-DIC folder, Heaviside-DIC folder)
#   out        : (standard-DIC png name, Heaviside-DIC png name)
FIELDS = [
    dict(
        name="displacement uy",
        component="uy",
        cmap="jet",
        pct=(1, 99),
        dirs=("Displacements", "Displacements_HDIC"),
        out=("displacement_tab_DIC.png", "displacement_tab_HDIC.png"),
    ),
    dict(
        name="strain von Mises",
        component="von_mises",
        cmap="viridis",
        pct=(1, 99),
        vmax_scale=1.3,  # slightly lower contrast on the strain maps
        dirs=("Strains", "Strains_HDIC"),
        out=("strain_DIC.png", "strain_HDIC.png"),
    ),
]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def load(folder, component):
    """Return (array, path). array is None when the file does not exist."""
    p = SRC / folder / f"{STEM}_{component}.tif"
    if not p.exists():
        return None, p
    return tifffile.imread(p).astype(np.float32), p


def to_png(data, vmin, vmax, cmap_name, out_path):
    """Apply the colormap and write an RGB PNG at native pixel resolution."""
    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
    cmap = colormaps[cmap_name].with_extremes(bad=(1, 1, 1, 1))  # NaN -> white
    rgba = cmap(norm(data))                                      # H x W x 4, float 0..1
    img = Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").convert("RGB")
    if SCALE != 1:
        img = img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    for f in FIELDS:
        dic_dir, hdic_dir = f["dirs"]
        dic, dic_p = load(dic_dir, f["component"])
        hdic, hdic_p = load(hdic_dir, f["component"])

        present = [a for a in (dic, hdic) if a is not None]
        if not present:
            print(f"[skip] {f['name']}: no source TIFF found "
                  f"({dic_p}, {hdic_p})")
            continue

        # Shared color scale over whichever images of the pair exist.
        stack = np.concatenate([a[np.isfinite(a)].ravel() for a in present])
        lo, hi = np.percentile(stack, f["pct"])
        hi = lo + (hi - lo) * f.get("vmax_scale", 1.0)
        print(f"[{f['name']}] cmap={f['cmap']} "
              f"vmin={lo:.4g} vmax={hi:.4g} (p{f['pct'][0]}-p{f['pct'][1]}"
              f", vmax_scale={f.get('vmax_scale', 1.0)})")

        for arr, src_p, out_name in (
            (dic, dic_p, f["out"][0]),
            (hdic, hdic_p, f["out"][1]),
        ):
            if arr is None:
                print(f"   missing: {src_p.relative_to(SRC)}  ->  "
                      f"{out_name} left unchanged")
                continue
            out = DEST / out_name
            to_png(arr, lo, hi, f["cmap"], out)
            print(f"   {src_p.relative_to(SRC)}  ->  "
                  f"screens/{out_name}  ({arr.shape[1]}x{arr.shape[0]})")


if __name__ == "__main__":
    main()
