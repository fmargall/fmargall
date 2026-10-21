"""Generate a generic animated repository header (SVG, dark + light) in GitHub's own colors.

Usage: py render_header.py "Title" "Tagline" [--out DIR] [--seed N] [--compact] [--static]
"""
import argparse
from pathlib import Path

import numpy as np

from render_profile import NAME_FONT, TAGLINE_FONT, text_to_svg_path

# --- Layouts: "full" for flagship repos, "compact" (shorter, sparser) for small ones ---
# Text sizes in px, positions baseline-left. The bands below are designed for "full";
# band_shift moves them vertically, amp_scale and density shrink them for the other layouts.
HEADER_W = 1280
LAYOUTS = {
    "full":    {"height": 320, "title": (52, (72, 128)), "tagline": (24, (74, 172)),
                "band_shift": 0, "amp_scale": 1.0, "density": 1.0},
    "compact": {"height": 200, "title": (44, (64, 84)), "tagline": (20, (66, 118)),
                "band_shift": -88, "amp_scale": 0.8, "density": 0.75},
}

# --- Point clouds: one band of scattered dots around each sinusoid, in the bottom of the frame ---
# base_y: mean height, amp: amplitude, wavelength: in px, sigma: vertical scatter, n: dot count
BANDS = [
    {"base_y": 252, "amp": 34, "wavelength": 980, "sigma": 5, "n": 320},
    {"base_y": 262, "amp": 30, "wavelength": 760, "sigma": 4, "n": 320},
    {"base_y": 274, "amp": 24, "wavelength": 1240, "sigma": 6, "n": 280},
]
DOT_R = (0.8, 1.9)       # dot radius range in px
DOT_OPACITY = (0.30, 0.85)
CORE_SIGMAS = 1.2        # dots fade with distance to their curve: a crisp core and a hazy fringe

# --- Traveling wave: a crest sweeping the clouds from left to right ---
WAVE_SPEED_PX_S = 180    # crest speed in px/s
WAVE_INTERVAL_S = 9.0    # time between two successive crests entering the frame
WAVE_WIDTH_PX = 220      # crest thickness in px
WAVE_SCALE = 1.6         # dot size multiplier at the crest
WAVE_DIM = 0.55          # opacity multiplier away from the crest

# --- Drift: every dot wanders along a small closed loop, very slowly ---
DRIFT_VARIANTS = 6       # number of distinct loops (dots pick one at random)
DRIFT_AMP_PX = 2.5       # loop size in px
DRIFT_PERIOD_S = (9, 17) # loop duration range in s
DRIFT_KEYS = 12          # keyframes per loop

# GitHub Primer colors: canvas.default -> canvas.subtle, fg.default, fg.muted, border.default
THEMES = {
    "dark":  {"bg_from": "#0D1117", "bg_to": "#151B23", "text": "#E6EDF3", "muted": "#9198A1",
              "border": "#3D444D"},
    "light": {"bg_from": "#FFFFFF", "bg_to": "#F6F8FA", "text": "#1F2328", "muted": "#59636E",
              "border": "#D1D9E0"},
}


def point_clouds(rng, layout):
    """Return dot positions, radii and opacities for all sinusoidal bands."""
    xs, ys, zs = [], [], []
    for band in BANDS:
        n = round(band["n"] * layout["density"])
        x = rng.uniform(-20, HEADER_W + 20, n)
        phase = rng.uniform(0, 2 * np.pi)
        amp = band["amp"] * layout["amp_scale"]
        curve = band["base_y"] + layout["band_shift"] + amp * np.sin(2 * np.pi * x / band["wavelength"] + phase)
        z = rng.normal(0, 1, n)                      # offset from the curve, in band sigmas
        xs.append(x)
        ys.append(curve + band["sigma"] * z)
        zs.append(z)
    x, y, z = np.concatenate(xs), np.concatenate(ys), np.concatenate(zs)
    radii = rng.uniform(*DOT_R, x.size)
    alpha = rng.uniform(*DOT_OPACITY, x.size) * np.exp(-0.5 * (z / CORE_SIGMAS) ** 2)
    return x, y, radii, alpha


def drift_keyframes(rng):
    """CSS keyframes for DRIFT_VARIANTS small Lissajous loops on the 'translate' property.

    'translate' is independent from the 'scale' the wave animates, so both run on the same circle.
    """
    css, periods = [], rng.uniform(*DRIFT_PERIOD_S, DRIFT_VARIANTS)
    for k, period in enumerate(periods):
        fx, fy = rng.choice([1, 2], 2)
        px, py = rng.uniform(0, 2 * np.pi, 2)
        steps = []
        for i in range(DRIFT_KEYS + 1):
            t = 2 * np.pi * i / DRIFT_KEYS
            dx = DRIFT_AMP_PX * np.sin(fx * t + px)
            dy = DRIFT_AMP_PX * np.sin(fy * t + py)
            steps.append(f"{100 * i / DRIFT_KEYS:.1f}% {{ translate: {dx:.2f}px {dy:.2f}px; }}")
        css.append(f"  @keyframes drift{k} {{ {' '.join(steps)} }}\n"
                   f"  .d{k} {{ animation-name: wave, drift{k}; "
                   f"animation-duration: {WAVE_INTERVAL_S}s, {period:.1f}s; }}")
    return "\n".join(css)


def render_header(title, tagline, theme, out_path, seed=0, layout_name="full", animated=True):
    colors = THEMES[theme]
    layout = LAYOUTS[layout_name]
    height = layout["height"]
    rng = np.random.default_rng(seed)                # same seed -> same dots in dark and light
    x, y, radii, alpha = point_clouds(rng, layout)
    variants = rng.integers(0, DRIFT_VARIANTS, x.size)
    drift_delays = -rng.uniform(0, DRIFT_PERIOD_S[1], x.size)

    # Same pulse timing as the banner: the crest reaches a dot at x after x / speed seconds,
    # delays mapped into (-interval, 0] so crests are already on screen at t=0.
    pulse_s = min(WAVE_WIDTH_PX / WAVE_SPEED_PX_S, WAVE_INTERVAL_S)
    rise = 0.5 * pulse_s / WAVE_INTERVAL_S
    fall = pulse_s / WAVE_INTERVAL_S
    arrival = (x + 20) / WAVE_SPEED_PX_S
    wave_delays = (arrival - rise * WAVE_INTERVAL_S) % WAVE_INTERVAL_S - WAVE_INTERVAL_S

    if animated:
        dots = "\n".join(
            f'<circle class="d{v}" cx="{a:.1f}" cy="{b:.1f}" r="{c:.2f}" fill-opacity="{o:.3f}" '
            f'style="animation-delay:{w:.2f}s,{d:.2f}s"/>'
            for a, b, c, o, v, w, d in zip(x, y, radii, alpha, variants, wave_delays, drift_delays))
    else:
        # Static: dots frozen at their resting opacity, no CSS at all
        dots = "\n".join(
            f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{c:.2f}" fill-opacity="{o * WAVE_DIM:.3f}"/>'
            for a, b, c, o in zip(x, y, radii, alpha))

    css = "" if not animated else f"""<style>
  circle {{ transform-box: fill-box; transform-origin: center; opacity: {WAVE_DIM};
           animation-timing-function: ease-in-out, linear; animation-iteration-count: infinite; }}
  @keyframes wave {{
    0%, {100 * fall:.2f}%, 100% {{ opacity: {WAVE_DIM}; scale: 1; }}
    {100 * rise:.2f}% {{ opacity: 1; scale: {WAVE_SCALE}; }}
  }}
{drift_keyframes(rng)}
  @media (prefers-reduced-motion: reduce) {{ circle {{ animation: none; }} }}
</style>"""

    title_size, title_pos = layout["title"]
    tagline_size, tagline_pos = layout["tagline"]
    title_d = text_to_svg_path(title, NAME_FONT, title_size, *title_pos)
    tagline_d = text_to_svg_path(tagline, TAGLINE_FONT, tagline_size, *tagline_pos)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {HEADER_W} {height}" width="{HEADER_W}" height="{height}">
<defs>
  {css}
  <clipPath id="frame"><rect width="{HEADER_W}" height="{height}" rx="14"/></clipPath>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{colors['bg_from']}"/>
    <stop offset="1" stop-color="{colors['bg_to']}"/>
  </linearGradient>
</defs>
<g clip-path="url(#frame)">
  <rect width="{HEADER_W}" height="{height}" fill="url(#bg)"/>
  <g fill="{colors['muted']}">
{dots}
  </g>
  <path d="{title_d}" fill="{colors['text']}"/>
  <path d="{tagline_d}" fill="{colors['text']}" fill-opacity="0.75"/>
</g>
<rect x="0.5" y="0.5" width="{HEADER_W - 1}" height="{height - 1}" rx="13.5" fill="none" stroke="{colors['border']}"/>
</svg>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("title")
    parser.add_argument("tagline")
    parser.add_argument("--out", type=Path, default=Path("."), help="output directory")
    parser.add_argument("--seed", type=int, default=0, help="changes the dot layout")
    parser.add_argument("--compact", action="store_true", help="shorter header with fewer dots")
    parser.add_argument("--static", action="store_true", help="no animation")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        render_header(args.title, args.tagline, theme, args.out / f"header_{theme}.svg", args.seed,
                      layout_name="compact" if args.compact else "full", animated=not args.static)
