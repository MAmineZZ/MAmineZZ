"""Generate self-contained dimensional technology tiles for the GitHub README.

No external assets, scripts, fonts, or network requests are needed by the SVGs.
Animation is decorative and stops for viewers requesting reduced motion.
"""
from pathlib import Path
from html import escape

OUTPUT = Path(__file__).resolve().parents[1] / 'assets' / 'v2'
TECHNOLOGIES = [
    ('csharp', 'C#', 'C#', '#c0abff', '#6d42d3'),
    ('dotnet', '.NET', '.NET', '#bc9bff', '#6036b3'),
    ('react', 'React', 'React', '#8ceaff', '#087e9d'),
    ('typescript', 'TypeScript', 'TS', '#8fc5ff', '#2466a9'),
    ('git', 'Git', 'Git', '#ffb2a7', '#ad4b48'),
]


def create_tile(slug: str, label: str, symbol: str, light: str, dark: str) -> str:
    """Draw a raised beveled tile with three shaded faces and readable labels."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="138" height="116" viewBox="0 0 138 116" role="img" aria-labelledby="title desc">
  <title id="title">{escape(label)}</title>
  <desc id="desc">A dimensional {escape(label)} technology tile with a gentle floating animation.</desc>
  <defs>
    <linearGradient id="face" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{light}"/><stop offset=".5" stop-color="{dark}"/><stop offset="1" stop-color="#182c51"/></linearGradient>
    <linearGradient id="top"><stop stop-color="#f0f9ff"/><stop offset="1" stop-color="{light}"/></linearGradient>
    <radialGradient id="aura"><stop stop-color="{light}" stop-opacity=".22"/><stop offset="1" stop-color="{dark}" stop-opacity="0"/></radialGradient>
  </defs>
  <style>
    .tile{{animation:float 4.8s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
    @keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
    @media(prefers-reduced-motion:reduce){{.tile{{animation:none}}}}
  </style>
  <rect x=".5" y=".5" width="137" height="115" rx="10" fill="#0c1523" stroke="#26374d"/>
  <ellipse cx="70" cy="72" rx="57" ry="25" fill="url(#aura)"/>
  <ellipse cx="70" cy="83" rx="32" ry="5" fill="#03070d"/>
  <g class="tile">
    <path d="M38 26 53 15 105 15 90 26Z" fill="url(#top)"/>
    <path d="M90 26 105 15 105 66 90 78Z" fill="{dark}"/>
    <rect x="38" y="26" width="52" height="52" rx="2" fill="url(#face)" stroke="{light}" stroke-opacity=".75"/>
    <path d="M42 32H86M42 35H60" stroke="white" opacity=".25"/>
    <text x="64" y="59" text-anchor="middle" fill="#ffffff" font-family="DejaVu Sans,Arial,sans-serif" font-size="{'13' if len(symbol)>3 else '19'}" font-weight="700">{escape(symbol)}</text>
    <path d="M94 33 101 28M94 39 101 34" stroke="{light}" opacity=".55"/>
  </g>
  <text x="69" y="103" text-anchor="middle" fill="#dfefff" font-family="DejaVu Sans,Arial,sans-serif" font-size="12" font-weight="600">{escape(label)}</text>
</svg>'''


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for technology in TECHNOLOGIES:
        (OUTPUT / f'tech-{technology[0]}.svg').write_text(create_tile(*technology), encoding='utf-8')
    print(f'Generated {len(TECHNOLOGIES)} SVG technology tiles.')
