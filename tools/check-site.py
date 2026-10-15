"""Validate generated links, fragments, metadata and sitemap before deployment."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links, self.canonicals, self.alternates = set(), [], [], []
        self.h1 = 0
        self.lang = self.description = self.title = ''
        self.in_title = False
        self.in_schema = False
        self.schema_text = ''
        self.schemas = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.add(a['id'])
        if tag == 'html':
            self.lang = a.get('lang')
        if tag == 'h1':
            self.h1 += 1
        if tag == 'title':
            self.in_title = True
        if tag == 'meta' and a.get('name') == 'description':
            self.description = a.get('content')
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonicals.append(a['href'])
        if tag == 'link' and a.get('rel') == 'alternate':
            self.alternates.append((a['hreflang'], a['href']))
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.in_schema = True
            self.schema_text = ''
        if tag in ('a', 'link', 'img'):
            self.links.append(a.get('href', a.get('src', '')))

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'script' and self.in_schema:
            self.schemas.append(json.loads(self.schema_text))
            self.in_schema = False

    def handle_data(self, value):
        if self.in_title:
            self.title += value
        if self.in_schema:
            self.schema_text += value


def check(output, base_url):
    base_url = base_url.rstrip('/') + '/'
    prefix = urlsplit(base_url).path
    pages = {p.relative_to(output).as_posix(): Page(p.read_text(encoding='utf-8')) for p in output.rglob('*.html')}
    failures, titles, canonicals = [], set(), set()
    for name, page in pages.items():
        if name != '404.html':
            if not page.description or not page.lang or page.h1 != 1 or not page.schemas:
                failures.append(f'{name}: missing metadata, schema, language or single H1')
            if len(page.canonicals) != 1 or not page.canonicals[0].startswith(base_url):
                failures.append(f'{name}: invalid canonical')
            elif page.canonicals[0] in canonicals:
                failures.append(f'{name}: duplicate canonical')
            canonicals.update(page.canonicals)
            if not page.title or page.title in titles:
                failures.append(f'{name}: missing or duplicate title')
            titles.add(page.title)
        for link in page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                if link.startswith(base_url):
                    local = unquote(parsed.path)[len(prefix):]
                else:
                    continue
            elif parsed.path.startswith(prefix):
                local = unquote(parsed.path)[len(prefix):]
            elif not parsed.path:
                local = name
            else:
                failures.append(f'{name}: unexpected relative link {link}')
                continue
            if not local or local.endswith('/'):
                local += 'index.html'
            if not (output / local).is_file():
                failures.append(f'{name}: broken link {link}')
            elif parsed.fragment and local in pages and unquote(parsed.fragment) not in pages[local].ids:
                failures.append(f'{name}: missing fragment {link}')
        for lang, url in page.alternates:
            if lang == 'x-default':
                continue
            path = urlsplit(url).path[len(prefix):]
            if not path or path.endswith('/'):
                path += 'index.html'
            target = pages.get(path)
            if not target or target.lang != lang or (page.lang, page.canonicals[0]) not in target.alternates:
                failures.append(f'{name}: non-reciprocal language alternate {url}')
    sitemap = ET.parse(output / 'sitemap.xml')
    urls = {e.text for e in sitemap.iter() if e.tag.endswith('loc')}
    if urls != canonicals:
        failures.append('sitemap does not match canonical pages')
    result = {'ok': not failures, 'pages': len(pages), 'sitemapUrls': len(urls), 'failures': failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'outputs/site')
    p.add_argument('--base-url', default='https://leileqithu.github.io/reverse-cli-anything/')
    args = p.parse_args()
    raise SystemExit(check(args.output, args.base_url))
