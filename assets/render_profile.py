"""Generate a Fibonacci (Vogel spiral) avatar (PNG), an animated banner (SVG, dark + light)
and a static social preview (PNG)."""
from pathlib import Path

import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D

# --- Pattern parameters ---
FAMILY = 21              # Fibonacci number: dots with same index mod FAMILY form one parastichy
PERIODS = 2              # number of intertwined spirals (gradient repeats PERIODS times around)
SHADE_MIN = 0.22         # dimmest opacity at the tail of each spiral
GAMMA = 1.6              # >1 sharpens the bright leading edge of each spiral
GOLDEN_ANGLE = np.pi * (3 - np.sqrt(5))

# --- Avatar parameters ---
AVATAR_N = 500
AVATAR_PX = 1024
AVATAR_THEME = "dark"    # background gradient + glow are taken from THEMES, like the banner
AVATAR_VIEW = 1.18       # half-width of the view in disk radii: margin for GitHub's circular crop
GLOW_RADIUS = 2.2        # glow radius in disk radii (shared by avatar and banner)

# --- Banner parameters ---
BANNER_W, BANNER_H = 1280, 320
BANNER_N = 500
BANNER_RADIUS = 148      # spiral radius in px (whole disk fits in the banner height)
BANNER_CENTER = (1080, 160)
ROTATION_PERIOD_S = 60   # one full turn, in seconds
WAVES = True             # radial waves pulsing through the dots
WAVE_SPEED_PX_S = 110    # how fast a crest travels outward, in px/s (disk radius is BANNER_RADIUS)
WAVE_INTERVAL_S = 5.0    # time between the emission of two successive waves at the center
WAVE_WIDTH_PX = 100      # crest thickness in px (stays constant when the speed changes)
WAVE_SCALE = 1.5         # dot size multiplier at the crest
WAVE_DIM = 0.55          # opacity multiplier in the trough

# --- Social preview parameters (static PNG for the repository settings) ---
SOCIAL_W, SOCIAL_H = 1280, 640
SOCIAL_THEME = "dark"
SOCIAL_RADIUS = 250      # spiral radius in px
SOCIAL_CENTER = (980, 320)
SOCIAL_NAME_SIZE = 72    # text sizes in px; positions are baseline-left
SOCIAL_NAME_POS = (96, 334)
SOCIAL_TAGLINE_SIZE = 32
SOCIAL_TAGLINE_POS = (99, 392)

NAME = "François Margall"
TAGLINE = "BRDF · Light transport · GPU computing"
FONTS_DIR = Path(__file__).parent / "fonts"
NAME_FONT = FONTS_DIR / "JosefinSans-SemiBold.ttf"
TAGLINE_FONT = FONTS_DIR / "JosefinSans-Thin.ttf"
# bg_from/bg_to: diagonal background gradient; glow: soft halo behind the spiral
THEMES = {
    "dark":  {"bg_from": "#0D2552", "bg_to": "#050F25", "glow": "#2A5CB8", "glow_opacity": 0.35,
              "dot": "#FFFFFF", "text": "#FFFFFF", "border_opacity": 0.10},
    "light": {"bg_from": "#FFFFFF", "bg_to": "#EDF1F8", "glow": "#C9D7EE", "glow_opacity": 0.70,
              "dot": "#081A3A", "text": "#081A3A", "border_opacity": 0.08},
}


def vogel(n_dots):
    """Return unit-disk positions, normalized radius and per-dot opacity."""
    n = np.arange(1, n_dots + 1)
    r = np.sqrt(n / n_dots)
    theta = n * GOLDEN_ANGLE
    x, y = r * np.cos(theta), r * np.sin(theta)

    # Residues k and k+1 are not neighbouring arms: sort arms by angle first
    k = np.arange(FAMILY)
    arm_rank = np.argsort(np.argsort((k * GOLDEN_ANGLE) % (2 * np.pi)))
    phase = arm_rank[n % FAMILY] / FAMILY            # position around the disk in [0, 1)

    # Sawtooth gradient repeated PERIODS times: bright head fading into a dim tail
    t = (PERIODS * phase) % 1.0
    shade = SHADE_MIN + (1 - SHADE_MIN) * t ** GAMMA
    alpha = shade * (0.60 + 0.40 * r)                # spiral gradient x mild center fade
    return x, y, r, alpha


def background_image(theme, width, height, center, glow_radius):
    """RGB image of the banner background: diagonal gradient plus a glow at center (in px)."""
    colors = THEMES[theme]
    to_rgb = lambda c: np.array(mcolors.to_rgb(c))
    u = np.linspace(0, 1, width)[None, :]
    v = np.linspace(0, 1, height)[:, None]
    t = (u + v) / 2                                  # 0 top-left -> 1 bottom-right, as the SVG gradient
    img = to_rgb(colors["bg_from"]) * (1 - t[..., None]) + to_rgb(colors["bg_to"]) * t[..., None]

    # Same falloff as the SVG radialGradient: opacity linear from glow_opacity at the center to 0
    px, py = np.arange(width)[None, :] + 0.5, np.arange(height)[:, None] + 0.5
    d = np.hypot(px - center[0], py - center[1])
    glow = colors["glow_opacity"] * np.clip(1 - d / glow_radius, 0, 1)
    return img * (1 - glow[..., None]) + to_rgb(colors["glow"]) * glow[..., None]


def render_avatar(out_path):
    x, y, r, alpha = vogel(AVATAR_N)
    sizes = 20 + 90 * r                              # matplotlib marker area, grows with radius
    colors = np.zeros((AVATAR_N, 4))
    colors[:, :3] = mcolors.to_rgb(THEMES[AVATAR_THEME]["dot"])
    colors[:, 3] = alpha                             # solid dot color, gradient in alpha

    dpi = 100
    fig = plt.figure(figsize=(AVATAR_PX / dpi, AVATAR_PX / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    disk_px = AVATAR_PX / (2 * AVATAR_VIEW)          # disk radius in px
    bg = background_image(AVATAR_THEME, AVATAR_PX, AVATAR_PX,
                          (AVATAR_PX / 2, AVATAR_PX / 2), GLOW_RADIUS * disk_px)
    ax.imshow(bg, interpolation="bilinear", zorder=0,
              extent=(-AVATAR_VIEW, AVATAR_VIEW, -AVATAR_VIEW, AVATAR_VIEW))
    ax.scatter(x, y, s=sizes, c=colors, linewidths=0, zorder=1)
    ax.set_xlim(-AVATAR_VIEW, AVATAR_VIEW)
    ax.set_ylim(-AVATAR_VIEW, AVATAR_VIEW)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print(f"Saved {out_path}")


def render_social_preview(out_path):
    """Static banner layout at the 2:1 size GitHub expects for a repository social preview."""
    colors = THEMES[SOCIAL_THEME]
    x, y, r, alpha = vogel(BANNER_N)
    cx, cy = SOCIAL_CENTER
    px = cx + SOCIAL_RADIUS * x
    py = cy - SOCIAL_RADIUS * y                      # image y axis points down, like the SVG
    radii = (1.3 + 1.9 * r) * SOCIAL_RADIUS / BANNER_RADIUS   # banner dot sizes, scaled up

    dpi = 100
    pt_per_px = 72 / dpi
    dot_colors = np.zeros((BANNER_N, 4))
    dot_colors[:, :3] = mcolors.to_rgb(colors["dot"])
    dot_colors[:, 3] = alpha

    # Axes in pixel units with the origin top-left, so every position matches the SVG banner
    fig = plt.figure(figsize=(SOCIAL_W / dpi, SOCIAL_H / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    bg = background_image(SOCIAL_THEME, SOCIAL_W, SOCIAL_H, SOCIAL_CENTER, GLOW_RADIUS * SOCIAL_RADIUS)
    ax.imshow(bg, interpolation="bilinear", zorder=0, extent=(0, SOCIAL_W, SOCIAL_H, 0))
    ax.scatter(px, py, s=(2 * radii * pt_per_px) ** 2, c=dot_colors, linewidths=0, zorder=1)

    for text, font, size, (tx, ty), opacity in [
            (NAME, NAME_FONT, SOCIAL_NAME_SIZE, SOCIAL_NAME_POS, 1.0),
            (TAGLINE, TAGLINE_FONT, SOCIAL_TAGLINE_SIZE, SOCIAL_TAGLINE_POS, 0.85)]:
        path = TextPath((0, 0), text, size=size, prop=FontProperties(fname=font))
        path = Affine2D().scale(1, -1).translate(tx, ty).transform_path(path)
        ax.add_patch(PathPatch(path, facecolor=colors["text"], alpha=opacity, linewidth=0, zorder=2))

    ax.set_xlim(0, SOCIAL_W)
    ax.set_ylim(SOCIAL_H, 0)
    ax.axis("off")
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print(f"Saved {out_path}")


def text_to_svg_path(text, font_file, size, x, y):
    """Outline text as an SVG path 'd' string, baseline-left anchored at (x, y).

    GitHub serves README images through <img>, which never loads external fonts,
    so the glyphs are baked in as geometry instead of relying on a font-family.
    """
    path = TextPath((0, 0), text, size=size, prop=FontProperties(fname=font_file))
    ops = {MplPath.MOVETO: "M", MplPath.LINETO: "L", MplPath.CURVE3: "Q", MplPath.CURVE4: "C"}
    parts = []
    for verts, code in path.iter_segments():
        if code == MplPath.CLOSEPOLY:
            parts.append("Z")
            continue
        pts = verts.reshape(-1, 2)
        coords = " ".join(f"{x + vx:.1f} {y - vy:.1f}" for vx, vy in pts)  # SVG y axis points down
        parts.append(f"{ops[code]}{coords}")
    return "".join(parts)


def render_banner(theme, out_path, animated=True):
    colors = THEMES[theme]
    x, y, r, alpha = vogel(BANNER_N)
    cx, cy = BANNER_CENTER
    px = cx + BANNER_RADIUS * x
    py = cy - BANNER_RADIUS * y                      # SVG y axis points down
    radii = 1.3 + 1.9 * r                            # dot radius in px, grows with distance

    # Only keep dots that can appear in the frame at some rotation angle
    dist = np.hypot(px - cx, py - cy)
    corner_reach = np.hypot(max(cx, BANNER_W - cx), max(cy, BANNER_H - cy))
    keep = dist <= corner_reach

    # Radial wave: each dot repeats the same pulse every WAVE_INTERVAL_S, and the crest reaches
    # a dot at distance d after d / WAVE_SPEED_PX_S seconds.
    # The pulse lasts as long as the crest takes to sweep over a dot; it cannot exceed the interval.
    pulse_s = min(WAVE_WIDTH_PX / WAVE_SPEED_PX_S, WAVE_INTERVAL_S)
    rise = 0.5 * pulse_s / WAVE_INTERVAL_S           # keyframe fraction where the crest peaks
    fall = pulse_s / WAVE_INTERVAL_S                 # keyframe fraction where the dot is back at rest

    # Peak time of a dot is delay + rise * interval; it must equal its arrival time (mod interval).
    # Mapping delays into (-interval, 0] starts every dot mid-cycle, so waves are present at t=0.
    arrival = dist / WAVE_SPEED_PX_S
    delays = (arrival - rise * WAVE_INTERVAL_S) % WAVE_INTERVAL_S - WAVE_INTERVAL_S

    dots = "\n".join(
        f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{c:.2f}" fill-opacity="{o:.3f}" '
        f'style="animation-delay:{d:.2f}s"/>'
        for a, b, c, o, d in zip(px[keep], py[keep], radii[keep], alpha[keep], delays[keep]))

    # One shared keyframe: a short pulse followed by rest until the next wave.
    # 'opacity' multiplies with each dot's own fill-opacity, keeping the spiral gradient.
    wave_css = f"""<style>
  circle {{ transform-box: fill-box; transform-origin: center;
           animation: wave {WAVE_INTERVAL_S}s ease-in-out infinite; }}
  @keyframes wave {{
    0%, {100 * fall:.2f}%, 100% {{ opacity: {WAVE_DIM}; transform: scale(1); }}
    {100 * rise:.2f}% {{ opacity: 1; transform: scale({WAVE_SCALE}); }}
  }}
  @media (prefers-reduced-motion: reduce) {{ circle {{ animation: none; }} }}
</style>""" if (animated and WAVES) else ""

    # SMIL rotation: works inside <img>, which is how GitHub renders README images
    anim = (f'<animateTransform attributeName="transform" type="rotate" '
            f'from="0 {cx} {cy}" to="360 {cx} {cy}" dur="{ROTATION_PERIOD_S}s" '
            f'repeatCount="indefinite"/>') if animated else ""

    name_d = text_to_svg_path(NAME, NAME_FONT, 54, 72, 168)
    tagline_d = text_to_svg_path(TAGLINE, TAGLINE_FONT, 24, 74, 214)

    # The fade is a mask on the dots (not an overlay) so the gradient background shows through.
    # The glow sits behind the spiral and gives the flat background some depth.
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BANNER_W} {BANNER_H}" width="{BANNER_W}" height="{BANNER_H}">
<defs>
  {wave_css}
  <clipPath id="frame"><rect width="{BANNER_W}" height="{BANNER_H}" rx="14"/></clipPath>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{colors['bg_from']}"/>
    <stop offset="1" stop-color="{colors['bg_to']}"/>
  </linearGradient>
  <radialGradient id="glow" gradientUnits="userSpaceOnUse" cx="{cx}" cy="{cy}" r="{GLOW_RADIUS * BANNER_RADIUS:.0f}">
    <stop offset="0" stop-color="{colors['glow']}" stop-opacity="{colors['glow_opacity']}"/>
    <stop offset="1" stop-color="{colors['glow']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="fade" x1="0" x2="1">
    <stop offset="0.45" stop-color="#FFFFFF" stop-opacity="0"/>
    <stop offset="0.70" stop-color="#FFFFFF" stop-opacity="1"/>
  </linearGradient>
  <mask id="fade-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="{BANNER_W}" height="{BANNER_H}">
    <rect width="{BANNER_W}" height="{BANNER_H}" fill="url(#fade)"/>
  </mask>
</defs>
<g clip-path="url(#frame)">
  <rect width="{BANNER_W}" height="{BANNER_H}" fill="url(#bg)"/>
  <rect width="{BANNER_W}" height="{BANNER_H}" fill="url(#glow)"/>
  <g mask="url(#fade-mask)">
    <g fill="{colors['dot']}">
      {anim}
{dots}
    </g>
  </g>
  <g fill="{colors['text']}">
    <path d="{name_d}"/>
    <path d="{tagline_d}" fill-opacity="0.85"/>
  </g>
</g>
<rect x="0.5" y="0.5" width="{BANNER_W - 1}" height="{BANNER_H - 1}" rx="13.5" fill="none"
      stroke="{colors['text']}" stroke-opacity="{colors['border_opacity']}"/>
</svg>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    render_avatar(f"avatar.png")
    render_social_preview("social_preview.png")
    for theme in THEMES:
        render_banner(theme, f"banner_{theme}.svg")
