"""Refresh text and calendar data inside the original Living Identity artwork."""

from collections import Counter
from datetime import date
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen


class ContributionCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.counts = {}
        self.tooltip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and 'ContributionCalendar-day' in attrs.get('class', '').split():
            self.days[attrs['id']] = (date.fromisoformat(attrs['data-date']), int(attrs['data-level']))
        elif tag == 'tool-tip':
            self.tooltip = attrs.get('for')

    def handle_data(self, data):
        if self.tooltip:
            match = re.match(r'\s*(No|[\d,]+) contributions?\b', data)
            if match:
                value = match[1]
                self.counts[self.tooltip] = 0 if value == 'No' else int(value.replace(',', ''))

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.tooltip = None


def get_calendar(user):
    url = f'https://github.com/users/{user}/contributions'
    request = Request(url, headers={'User-Agent': 'profile-readme-updater', 'Accept-Language': 'en'})
    with urlopen(request, timeout=30) as response:
        parser = ContributionCalendar()
        parser.feed(response.read().decode('utf-8'))
    days = sorted((day, level, parser.counts.get(key)) for key, (day, level) in parser.days.items())
    if not 365 <= len(days) <= 371 or days[0][0].weekday() != 6 or any(
        (day - days[0][0]).days != i or count is None or level not in range(5)
        for i, (day, level, count) in enumerate(days)
    ):
        raise ValueError('Incomplete GitHub contribution calendar')
    return days


def replace_once(svg, pattern, replacement):
    result, count = re.subn(pattern, replacement, svg)
    if count != 1:
        raise ValueError(f'Expected one SVG match for {pattern!r}, found {count}')
    return result


def update_text(svg, attributes, value):
    pattern = rf'(<text {re.escape(attributes)}[^>]*>)[^<]*(</text>)'
    return replace_once(svg, pattern, lambda match: match[1] + escape(str(value)) + match[2])


def project_metadata(repo):
    if repo is None:
        return 'Unavailable on public GitHub'
    stars = repo['stargazers_count']
    return f"{repo['language'] or '—'} · {stars} {'star' if stars == 1 else 'stars'}"


def render_artwork(profile, repositories, days):
    assets = Path('assets')
    artwork = {name: (assets / f'p3-{name}.svg').read_text(encoding='utf-8') for name in (
        'hero', 'highlights', 'projects-wow', 'timeline', 'stack', 'stats', 'heatmap',
    )}
    total = sum(count for _, _, count in days)
    repo_count = profile['public_repos']
    stars = sum(repo['stargazers_count'] for repo in repositories)
    for fill, value in (('#ecf4ff', repo_count), ('#38bdf8', f'{stars} ★'), ('#00ffa3', total)):
        pattern = rf'(<text y="36" fill="{fill}" font-size="28" font-weight="800">)\d+(?: ★)?(</text>)'
        artwork['hero'] = replace_once(artwork['hero'], pattern, lambda match: f'{match[1]}{value}{match[2]}')
    for x, value in zip((48, 286, 524, 762), (repo_count, stars, total, profile['followers'])):
        artwork['stats'] = update_text(artwork['stats'], f'x="{x}" y="220"', value)
    artwork['highlights'] = update_text(artwork['highlights'], 'x="668" y="273"', f'{repo_count} Repos: AgentLedger,')

    by_name = {repo['name'].casefold(): repo for repo in repositories}
    for x, y, name in ((500, 357, 'AgentLedger'), (190, 297, 'TokenWatch'), (805, 267, 'CityMirror'), (760, 452, 'OpenAutomationHub')):
        artwork['projects-wow'] = update_text(artwork['projects-wow'], f'x="{x}" y="{y}"', project_metadata(by_name.get(name.casefold())))

    for index, (x, y, name) in enumerate(((120, 167, 'WASM-Sandbox'), (370, 365, 'forfettario-kit'), (620, 167, 'pokematrix'), (870, 365, 'TorinoTramTour')), 1):
        repo = by_name.get(name.casefold())
        if repo:
            created = date.fromisoformat(repo['created_at'][:10]).strftime('%b %Y')
            description = ' '.join((repo['description'] or '—').split())
            description = description[:31].rstrip() + '…' if len(description) > 32 else description
        else:
            created, description = '—', '—'
        for row, value in ((y, f'{index:02}  /  {created}'), (216 if y == 167 else 339, description), (236 if y == 167 else 358, project_metadata(repo))):
            artwork['timeline'] = update_text(artwork['timeline'], f'x="{x}" y="{row}"', value)

    languages = Counter(repo['language'] for repo in repositories)
    for x, y, language in ((48, 220, 'TypeScript'), (286, 220, 'HTML'), (524, 220, 'Python'), (762, 220, 'JavaScript'), (48, 355, 'CSS')):
        share = languages[language] / repo_count if repo_count else 0
        artwork['stack'] = update_text(artwork['stack'], f'x="{x}" y="{y}"', f'{share:.0%} of public repos')
        bar = rf'(<path class="draw" pathLength="1" d="M{x} {y + 19}h)[\d.]+'
        artwork['stack'] = replace_once(artwork['stack'], bar, lambda match: f'{match[1]}{190 * share:.2f}')

    dots = []
    for i, (day, level, count) in enumerate(days):
        column, row = divmod(i, 7)
        css_class, color = ('twinkle', '#779dff') if count else ('', '#93a6c4')
        radius = 2 + level * 1.5
        opacity = (0.16, 0.40, 0.55, 0.73, 0.95)[level]
        dots.append(f'<circle class="{css_class}" style="animation-delay:-{column * 0.13 + row * 0.21:.2f}s" '
                    f'cx="{48 + column * 17}" cy="{172 + row * 30}" r="{radius:g}" fill="{color}" '
                    f'opacity="{opacity:.2f}"><title>{day}: {count} contributions</title></circle>')
    dot = r'<circle[^>]*><title>\d{4}-\d{2}-\d{2}: \d+ contributions</title></circle>'
    artwork['heatmap'] = replace_once(artwork['heatmap'], f'(?:{dot})+', lambda _: ''.join(dots))
    artwork['heatmap'] = update_text(artwork['heatmap'], 'x="48" y="435"', f'{total} contributions · brighter stars mark busier days')
    return {assets / f'p3-{name}.svg': svg for name, svg in artwork.items()}
