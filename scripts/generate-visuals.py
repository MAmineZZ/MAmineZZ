#!/usr/bin/env python3
"""Generate self-contained, accessible GitHub profile illustrations.

The core uses perspective-projected 3D vertices, not an image or a rotating flat
icon. SVG SMIL interpolates the projected triangle geometry and face lighting.
All referenced definitions are local. No script, foreignObject, fonts, API, or
remote image is required at render time. Viewers without SMIL display the first
frame; reduced-motion CSS swaps the animation for its static first frame. The
separate system-core-still.svg is an explicit fallback for <picture> consumers.

Run: python scripts/generate-visuals.py
Optional GIF export (requires Inkscape and Pillow): append --gif
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import math
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "v2"
TAU = 2 * math.pi
FRAMES = 49  # Includes the repeated first frame for a seamless sixteen-second loop.
DURATION = "16s"


def fmt(value: float) -> str:
    return f"{value:.2f}"


def turn(vertex: tuple[float, float, float], angle: float) -> tuple[float, float, float]:
    x, y, z = vertex
    co, si = math.cos(angle), math.sin(angle)
    return (x * co + z * si, y, -x * si + z * co)


def camera(vertex: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vertex
    elevation = 0.38
    return (x, y * math.cos(elevation) - z * math.sin(elevation),
            y * math.sin(elevation) + z * math.cos(elevation))


def project(vertex: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = camera(vertex)
    perspective = 520 / (520 + z)
    return (220 + x * perspective, 151 - y * perspective)


def path_for(vertices: list[tuple[float, float, float]], closed: bool = True) -> str:
    points = [project(v) for v in vertices]
    return "M" + " L".join(f"{fmt(x)},{fmt(y)}" for x, y in points) + (" Z" if closed else "")


def animate(attribute: str, values: list[str], duration: str = DURATION) -> str:
    return (f'<animate attributeName="{attribute}" dur="{duration}" '
            f'values="{";".join(values)}" repeatCount="indefinite" calcMode="linear"/>')


VERTICES = [(0, 91, 0), (67, 0, 0), (0, 0, 67), (-67, 0, 0), (0, 0, -67), (0, -87, 0)]
FACES = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1),
         (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
ANGLES = [0.48 + TAU * i / (FRAMES - 1) for i in range(FRAMES)]


def lighting(vertices: list[tuple[float, float, float]]) -> tuple[str, str]:
    # Normals are computed in camera space, so front facets remain solid while
    # reverse facets are faint holographic wireframe throughout the rotation.
    a, b, c = [camera(v) for v in vertices]
    u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
    normal = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    length = math.sqrt(sum(n * n for n in normal))
    normal = [n / length for n in normal]
    light = max(0, -0.47 * normal[0] + 0.66 * normal[1] - 0.58 * normal[2])
    facing = max(0, min(1, (-normal[2] + 0.11) / 0.26))
    opacity = 0.025 + facing * 0.86
    # Cool cyan on lit planes; violet on the shaded lower planes.
    lower = sum(v[1] for v in vertices) < 0
    base = (68, 55, 154) if lower else (14, 85, 116)
    peak = (148, 151, 247) if lower else (99, 246, 236)
    rgb = [round(base[i] + light * (peak[i] - base[i])) for i in range(3)]
    return ("#" + "".join(f"{channel:02x}" for channel in rgb), fmt(opacity))


def crystal(animated: bool) -> str:
    output = []
    for face in FACES:
        series = [[turn(VERTICES[i], angle) for i in face] for angle in ANGLES]
        paths = [path_for(vertices) for vertices in series]
        colors, opacity = zip(*(lighting(vertices) for vertices in series))
        output.append(f'<path d="{paths[0]}" fill="{colors[0]}" fill-opacity="{opacity[0]}" '
                      'stroke="#9cefeb" stroke-opacity=".52" stroke-width=".8" stroke-linejoin="round">')
        if animated:
            output.extend([animate("d", paths), animate("fill", list(colors)), animate("fill-opacity", list(opacity))])
        output.append('</path>')
    # Bright equator adds physical thickness and legibility at README scale.
    paths = [path_for([turn(VERTICES[i], angle) for i in (1, 2, 3, 4)]) for angle in ANGLES]
    output.append(f'<path d="{paths[0]}" fill="none" stroke="#b4fff6" stroke-opacity=".8" stroke-width="1.1">')
    if animated:
        output.append(animate("d", paths))
    output.append('</path>')
    return "".join(output)


def orbit_point(theta: float, tilt: float) -> tuple[float, float, float]:
    x, z = math.cos(theta) * 113, math.sin(theta) * 113
    return (x, z * math.sin(tilt), z * math.cos(tilt))


def orbit(animated: bool) -> str:
    output = []
    for tilt, color, phase in [(0.52, "#59e3db", 0.1), (-0.62, "#a794ff", 3.7)]:
        pts = [orbit_point(TAU * i / 80, tilt) for i in range(81)]
        output.append(f'<path d="{path_for(pts)}" fill="none" stroke="{color}" stroke-opacity=".25" stroke-width=".7"/>')
        positions = [project(orbit_point(angle + phase, tilt)) for angle in ANGLES]
        output.append(f'<circle cx="{fmt(positions[0][0])}" cy="{fmt(positions[0][1])}" r="3" fill="{color}" filter="url(#glow)">')
        if animated:
            output.append(animate("cx", [fmt(p[0]) for p in positions]))
            output.append(animate("cy", [fmt(p[1]) for p in positions]))
        output.append('</circle>')
    return "".join(output)


def core_svg(animated: bool) -> str:
    scene = crystal(animated=True) + orbit(animated=True) if animated else crystal(False) + orbit(False)
    still = crystal(False) + orbit(False)
    # No misleading live metrics: the small typography names the design and
    # its engineering theme, not a real backend or activity monitoring service.
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="440" height="340" viewBox="0 0 440 340" role="img" aria-labelledby="title desc">
<title id="title">System core — an animated holographic crystal</title>
<desc id="desc">A faceted three-dimensional cyan and violet crystal gently rotates above concentric platform rings. Two light particles orbit it. Decorative illustration; no activity data. A static first frame is shown when motion is reduced or animation is unsupported.</desc>
<defs>
  <linearGradient id="panel" x2="0" y2="1"><stop stop-color="#111b31"/><stop offset="1" stop-color="#080e1b"/></linearGradient>
  <radialGradient id="ambient"><stop stop-color="#246f84" stop-opacity=".25"/><stop offset="1" stop-color="#0c1426" stop-opacity="0"/></radialGradient>
  <radialGradient id="floor"><stop stop-color="#62e7d7" stop-opacity=".22"/><stop offset=".57" stop-color="#507acc" stop-opacity=".12"/><stop offset="1" stop-color="#507acc" stop-opacity="0"/></radialGradient>
  <linearGradient id="ring"><stop stop-color="#50c9c7" stop-opacity=".12"/><stop offset=".5" stop-color="#7fffea" stop-opacity=".6"/><stop offset="1" stop-color="#a590f7" stop-opacity=".26"/></linearGradient>
  <linearGradient id="column" x2="0" y2="1"><stop stop-color="#6cefe2" stop-opacity="0"/><stop offset="1" stop-color="#6cefe2" stop-opacity=".08"/></linearGradient>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <clipPath id="bounds"><rect x=".5" y=".5" width="439" height="339" rx="18"/></clipPath>
</defs>
<style>
 .still {{display:none}}
 .orbit-trace {{animation:flow 16s linear infinite}}
 @keyframes flow {{to {{stroke-dashoffset:-152}}}}
 @media (prefers-reduced-motion:reduce) {{.motion {{display:none}} .still {{display:inline}} .orbit-trace {{animation:none}}}}
</style>
<g clip-path="url(#bounds)">
<rect width="440" height="340" rx="18" fill="url(#panel)"/>
<ellipse cx="220" cy="160" rx="200" ry="161" fill="url(#ambient)"/>
<g stroke="#7292b4" stroke-opacity=".08" stroke-width=".7">
  <path d="M0 208H440M0 221H440M0 239H440M0 264H440M0 302H440"/>
  <path d="M220 183L-100 340M220 183L20 340M220 183L135 340M220 183V340M220 183L305 340M220 183L420 340M220 183L540 340"/>
</g>
<path d="M32 57V49H63M377 49H408V57M32 278V286H63M377 286H408V278" fill="none" stroke="#86a6c4" stroke-opacity=".23"/>
<text x="24" y="28" fill="#d1dee9" font-family="ui-monospace,monospace" font-size="10" letter-spacing="2.1">SYSTEM CORE</text>
<path d="M372 22h8m-4-4v8M389 18h8v8h-8zM406 19l5 6m0-6l-5 6" fill="none" stroke="#7a8eaa" stroke-width=".9"/>
<ellipse cx="220" cy="247" rx="160" ry="47" fill="url(#floor)"/>
<path d="M169 196L148 249Q220 278 292 249L271 196Z" fill="url(#column)"/>
<g fill="none" stroke="url(#ring)">
  <ellipse cx="220" cy="247" rx="127" ry="38" stroke-width="1"/>
  <ellipse cx="220" cy="247" rx="104" ry="30" stroke-width=".7"/>
  <ellipse cx="220" cy="247" rx="81" ry="22" stroke-width="1.5"/>
  <ellipse cx="220" cy="251" rx="81" ry="22" stroke-width=".6" opacity=".4"/>
</g>
<ellipse class="orbit-trace" cx="220" cy="247" rx="116" ry="34" fill="none" stroke="#7de7df" stroke-opacity=".32" stroke-width="1.5" stroke-dasharray="24 14 5 14 4 91"/>
<ellipse cx="220" cy="247" rx="27" ry="7" fill="#a0faf3" opacity=".09" filter="url(#glow)"/>
<path d="M220 227v17" fill="none" stroke="#81e7de" stroke-opacity=".4" stroke-dasharray="2 3"/>
<g {'class="motion"' if animated else ''}>{scene}</g>
{f'<g class="still">{still}</g>' if animated else ''}
<g fill="none" stroke="#89bdce" stroke-width=".7" opacity=".4">
  <path d="M69 128h20l11 11M342 198l11-11h18"/>
  <circle cx="66" cy="128" r="2"/><circle cx="374" cy="187" r="2"/>
  <path d="M61 163h4m-2-2v4M365 101h4m-2-2v4"/>
</g>
<path d="M24 306H416" stroke="#8ba5c3" stroke-opacity=".15"/>
<text x="24" y="324" fill="#8095b0" font-family="ui-monospace,monospace" font-size="8" letter-spacing="1.35">ENGINEERING IN PROGRESS</text>
<text x="416" y="324" text-anchor="end" fill="#95c9d2" font-family="ui-monospace,monospace" font-size="8" letter-spacing="1.2">BUILD / LEARN / ITERATE</text>
</g>
<rect x=".5" y=".5" width="439" height="339" rx="18" fill="none" stroke="#233449"/>
</svg>'''
    if not animated:
        svg = svg.replace("an animated holographic", "a holographic").replace('class="orbit-trace"', '')
    return svg


def divider_svg() -> str:
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="44" viewBox="0 0 900 44" role="img" aria-labelledby="title desc">
<title id="title">Holographic signal divider</title>
<desc id="desc">A thin cyan and violet circuit connects three shaded geometric diamonds. A subtle light flows along the circuit. Motion stops when reduced motion is preferred; the static circuit remains visible.</desc>
<defs>
 <linearGradient id="beam"><stop stop-color="#55ded8" stop-opacity="0"/><stop offset=".18" stop-color="#55ded8" stop-opacity=".3"/><stop offset=".5" stop-color="#92cff0" stop-opacity=".7"/><stop offset=".82" stop-color="#ad92ef" stop-opacity=".3"/><stop offset="1" stop-color="#ad92ef" stop-opacity="0"/></linearGradient>
 <linearGradient id="flare"><stop stop-color="#55ded8" stop-opacity="0"/><stop offset=".5" stop-color="#adf7ee" stop-opacity=".8"/><stop offset="1" stop-color="#ad92ef" stop-opacity="0"/></linearGradient>
 <filter id="soft" x="-50%" y="-300%" width="200%" height="700%"><feGaussianBlur stdDeviation="1.7"/></filter>
 <clipPath id="signal"><rect x="80" y="15" width="740" height="14"/></clipPath>
</defs>
<style>
 .light {animation:transmit 10s linear infinite}
 @keyframes transmit {from {transform:translateX(-140px)} to {transform:translateX(940px)}}
 @media (prefers-reduced-motion:reduce) {.light {animation:none;opacity:0}}
</style>
<path d="M16 22H327L339 15H415M485 15H561L573 22H884" fill="none" stroke="url(#beam)" stroke-width="1"/>
<path d="M105 27H278L286 22M622 22L630 27H795" fill="none" stroke="url(#beam)" stroke-width=".65" opacity=".5"/>
<g clip-path="url(#signal)"><path class="light" d="M-55 22H55" stroke="url(#flare)" stroke-width="2" filter="url(#soft)"/></g>
<g stroke="#91dadb" stroke-width=".65" stroke-linejoin="round">
 <path d="M438 22L450 6L462 22L450 37Z" fill="#182e48"/>
 <path d="M450 6L462 22L450 19Z" fill="#70cbd1"/>
 <path d="M450 6L450 19L438 22Z" fill="#26768c"/>
 <path d="M438 22L450 19L450 37Z" fill="#315b85"/>
 <path d="M450 19L462 22L450 37Z" fill="#796fb9"/>
</g>
<g stroke-width=".6" stroke-linejoin="round">
 <path d="M414 22L420 14L426 22L420 30Z" fill="#214558" stroke="#62b5bd"/>
 <path d="M420 14L426 22L420 20Z" fill="#78b7c3"/><path d="M420 20L426 22L420 30Z" fill="#427184"/>
 <path d="M474 22L480 14L486 22L480 30Z" fill="#413d68" stroke="#a69ad1"/>
 <path d="M480 14L486 22L480 20Z" fill="#aba3da"/><path d="M480 20L486 22L480 30Z" fill="#7b6baf"/>
</g>
<path d="M388 22h10m104 0h10" stroke="#8cc9d8" opacity=".5"/>
</svg>'''


def render_gif() -> None:
    """Rasterize our native geometry offline, using one shared GIF palette.

    The generated artwork is never processed here: only the procedural SVG
    above is rendered. Temporary frames are discarded after the GIF is saved.
    """
    from PIL import Image

    renderer = shutil.which("inkscape")
    if not renderer:
        raise RuntimeError("The optional GIF export requires Inkscape on PATH.")
    global ANGLES
    original_angles = ANGLES
    frame_count = 160
    with TemporaryDirectory(prefix="profile-core-") as directory:
        temporary = Path(directory)
        sources = []
        try:
            for frame in range(frame_count):
                ANGLES = [0.48 + TAU * frame / frame_count]
                source = temporary / f"core-{frame:03}.svg"
                source.write_text(core_svg(animated=False), encoding="utf-8")
                sources.append(source)
        finally:
            ANGLES = original_angles

        def render(source: Path) -> Path:
            output = source.with_suffix(".png")
            subprocess.run([renderer, str(source), "--export-type=png",
                            f"--export-filename={output}"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return output

        with ThreadPoolExecutor(max_workers=4) as executor:
            pngs = list(executor.map(render, sources))
        frames = []
        for path in pngs:
            # SVG corners are transparent. Simply converting RGBA to RGB keeps
            # their hidden color, which can become a bright palette artifact.
            # Composite explicitly so GIFs have stable opaque navy corners in
            # every viewer and do not depend on disposal/transparency support.
            with Image.open(path) as png:
                rgba = png.convert("RGBA")
                matte = Image.new("RGBA", rgba.size, "#0d1627")
                frames.append(Image.alpha_composite(matte, rgba).convert("RGB"))
        # Sample the entire rotation so moving faces share a stable palette.
        atlas = Image.new("RGB", (440 * 4, 340 * 4))
        for index in range(16):
            atlas.paste(frames[index * 10], ((index % 4) * 440, (index // 4) * 340))
        palette = atlas.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
        quantized = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
        output = OUT / "system-core.gif"
        quantized[0].save(output, save_all=True, append_images=quantized[1:],
                          duration=100, loop=0, optimize=True, disposal=1)
        frames[0].save(OUT / "system-core-still.png", optimize=True)
        print(f"{output}: {output.stat().st_size:,} bytes; {frame_count} frames, 16 seconds")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gif", action="store_true", help="Also export animated GIF and static PNG with Inkscape.")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "system-core.svg": core_svg(animated=True),
        "system-core-still.svg": core_svg(animated=False),
        "signal-divider.svg": divider_svg(),
    }
    for name, content in files.items():
        ElementTree.fromstring(content)
        path = OUT / name
        path.write_text(content + "\n", encoding="utf-8")
        print(f"{path}: {path.stat().st_size:,} bytes")
    if args.gif:
        render_gif()


if __name__ == "__main__":
    main()
