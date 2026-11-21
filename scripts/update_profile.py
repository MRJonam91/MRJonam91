"""Refresh the public GitHub section of the profile README."""
import html
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

USER = 'MRJonam91'
START = '<!-- github-data:start -->'
END = '<!-- github-data:end -->'


def render(profile, repositories):
    stars = sum(repo['stargazers_count'] for repo in repositories)
    projects = sorted((r for r in repositories if not r['fork'] and not r['archived'] and r['name'].casefold() != USER.casefold()), key=lambda r: (r['pushed_at'] or '', r['name']), reverse=True)[:6]
    lines = [
        '## GitHub in numeri / GitHub at a glance', '',
        f"**{profile['public_repos']} repository pubbliche** · **{stars} stelle** · **{profile['followers']} follower**", '',
        'Stelle ricevute da tutte le repository pubbliche personali, inclusi fork e archivi. / Stars received across all personal public repositories, including forks and archived repositories.', '',
        '### Repository aggiornate di recente / Recently updated repositories', '',
        'Ultimi push; escluse repository archiviate, fork e questa pagina. / Latest pushes; excluding archived repositories, forks and this profile.', '',
        '| Repository | Descrizione / Description | Stelle / Stars |', '|---|---|---:|',
    ]
    for repo in projects:
        name = html.escape(repo['name']).replace('|', '&#124;')
        description = html.escape(' '.join((repo['description'] or '—').split())).replace('|', '&#124;')
        lines.append(f"| [{name}]({repo['html_url']}) | {description} | {repo['stargazers_count']} |")
    if not projects:
        lines.append('| — | Nessuna repository disponibile / No repositories available | — |')
    lines += ['', '[Tutte le repository pubbliche / All public repositories](https://github.com/MRJonam91?tab=repositories)', '', '<sub>Dati pubblici GitHub aggiornati ogni giorno tramite GitHub Actions. / Public GitHub data refreshed daily by GitHub Actions.</sub>']
    return '\n'.join(lines)


def replace_section(source, content):
    if source.count(START) != 1 or source.count(END) != 1 or source.index(START) > source.index(END):
        raise ValueError('Expected exactly one ordered pair of GitHub data markers')
    before, rest = source.split(START)
    _, after = rest.split(END)
    return before + START + '\n' + content + '\n' + END + after


def get_json(url):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-readme-updater', 'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def main():
    profile = get_json(f'https://api.github.com/users/{USER}')
    repositories = []
    page = 1
    while True:
        batch = get_json(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch, list):
            raise ValueError('Unexpected repository response')
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    if len(repositories) != profile['public_repos']:
        raise ValueError('Incomplete repository list; refusing to publish inaccurate counts')
    path = Path('README.md')
    original = path.read_text(encoding='utf-8')
    path.write_text(replace_section(original, render(profile, repositories)), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
