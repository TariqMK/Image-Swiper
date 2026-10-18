"""Select a SemVer greater than all releases (including drafts) and tags."""
import argparse
import json
import os
from pathlib import Path
import re
import tomllib
from urllib.request import Request, urlopen

VERSION = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$')


def next_version(current, names, bump):
    versions = []
    for name in [current, *names]:
        match = VERSION.fullmatch(name)
        if match:
            versions.append(tuple(map(int, match.groups())))
    if not versions:
        raise ValueError('No valid baseline version found')
    major, minor, patch = max(versions)
    if bump == 'major':
        return f'{major + 1}.0.0'
    if bump == 'minor':
        return f'{major}.{minor + 1}.0'
    if bump == 'patch':
        return f'{major}.{minor}.{patch + 1}'
    raise ValueError(f'Unknown bump: {bump}')


def list_pages(endpoint):
    api = os.environ.get('GITHUB_API_URL', 'https://api.github.com')
    repository = os.environ['GITHUB_REPOSITORY']
    page = 1
    while True:
        request = Request(f'{api}/repos/{repository}/{endpoint}?per_page=100&page={page}', headers={
            'Authorization': f'Bearer {os.environ["GH_TOKEN"]}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        })
        with urlopen(request, timeout=30) as response:
            items = json.load(response)
        yield from items
        if len(items) < 100:
            break
        page += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bump', choices=['major', 'minor', 'patch'])
    args = parser.parse_args()
    project = Path('pyproject.toml')
    text = project.read_text(encoding='utf-8')
    current = tomllib.loads(text)['project']['version']
    # The authenticated releases endpoint includes drafts, unlike /releases/latest.
    names = [release['tag_name'] for release in list_pages('releases')]
    names.extend(tag['name'] for tag in list_pages('tags'))
    version = next_version(current, names, args.bump)
    text, count = re.subn(r'(?m)^version = "[^"\n]+"$', f'version = "{version}"', text)
    if count != 1:
        raise RuntimeError('Expected exactly one project version')
    project.write_text(text, encoding='utf-8')
    Path('image_swiper/version.py').write_text(
        f'"""Application version, updated in each tagged release commit."""\n__version__ = "{version}"\n',
        encoding='utf-8',
    )
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write(f'version={version}\ntag=v{version}\n')
    print(f'Reserved version: v{version}')


if __name__ == '__main__':
    main()
