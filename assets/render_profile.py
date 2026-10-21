"""Generate a Fibonacci (Vogel spiral) avatar (PNG) and an animated banner (SVG, dark + light)."""
import numpy as np
import matplotlib.pyplot as plt

# --- Pattern parameters ---
FAMILY = 21              # Fibonacci number: dots with same index mod FAMILY form one parastichy
PERIODS = 2              # number of intertwined spirals (gradient repeats PERIODS times around)
SHADE_MIN = 0.22         # dimmest opacity at the tail of each spiral
GAMMA = 1.6              # >1 sharpens the bright leading edge of each spiral
GOLDEN_ANGLE = np.pi * (3 - np.sqrt(5))

# --- Avatar parameters ---
AVATAR_N = 500
AVATAR_PX = 1024
BACKGROUND = "#081A3A"

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
NAME = "François Margall"
TAGLINE = "BRDF · Light transport · GPU computing"
THEMES = {
    "dark":  {"bg": "#081A3A", "dot": "#FFFFFF", "text": "#FFFFFF"},
    "light": {"bg": "#FFFFFF", "dot": "#081A3A", "text": "#081A3A"},
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


def render_avatar(out_path):
    x, y, r, alpha = vogel(AVATAR_N)
    sizes = 20 + 90 * r                              # matplotlib marker area, grows with radius
    colors = np.ones((AVATAR_N, 4))
    colors[:, 3] = alpha                             # pure white, gradient in alpha

    dpi = 100
    fig = plt.figure(figsize=(AVATAR_PX / dpi, AVATAR_PX / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(BACKGROUND)
    ax.scatter(x, y, s=sizes, c=colors, linewidths=0)
    # Margin so the disk survives GitHub's circular crop
    ax.set_xlim(-1.18, 1.18)
    ax.set_ylim(-1.18, 1.18)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(out_path, dpi=dpi, facecolor=BACKGROUND)
    plt.close(fig)
    print(f"Saved {out_path}")


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

    # A soft fade on the left keeps the name readable over the spiral
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BANNER_W} {BANNER_H}" width="{BANNER_W}" height="{BANNER_H}">
<defs>
  {wave_css}
  <clipPath id="frame"><rect width="{BANNER_W}" height="{BANNER_H}" rx="14"/></clipPath>
  <linearGradient id="fade" x1="0" x2="1">
    <stop offset="0.45" stop-color="{colors['bg']}" stop-opacity="1"/>
    <stop offset="0.70" stop-color="{colors['bg']}" stop-opacity="0"/>
  </linearGradient>
</defs>
<g clip-path="url(#frame)">
  <rect width="{BANNER_W}" height="{BANNER_H}" fill="{colors['bg']}"/>
  <g fill="{colors['dot']}">
    {anim}
{dots}
  </g>
  <rect width="{BANNER_W}" height="{BANNER_H}" fill="url(#fade)"/>
  <g fill="{colors['text']}" font-family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="72" y="168" font-size="52" font-weight="600" letter-spacing="0.5">{NAME}</text>
    <text x="74" y="212" font-size="20" fill-opacity="0.72">{TAGLINE}</text>
  </g>
</g>
</svg>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    render_avatar(f"avatar.png")
    for theme in THEMES:
        render_banner(theme, f"banner_{theme}.svg")
