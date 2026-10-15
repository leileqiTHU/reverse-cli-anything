"""Build a static, bilingual documentation site from tracked Markdown sources."""
import argparse
import html
from html.parser import HTMLParser
import json
import posixpath
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET

import markdown

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/leileqiTHU/reverse-cli-anything'
RAW = 'https://raw.githubusercontent.com/leileqiTHU/reverse-cli-anything/main/'
DEFAULT_URL = 'https://leileqithu.github.io/reverse-cli-anything/'


def slug(value, separator):
    # Match GitHub headings, including Chinese and Unicode punctuation handling.
    value = re.sub(r'<[^>]+>', '', html.unescape(value)).lower()
    return re.sub(r'\s', separator, re.sub(r'[^\w\- ]', '', value))


def sources():
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    names = set(tracked) | {
        'docs/faq.md', 'docs/faq.zh-CN.md',
        'docs/desktop-automation.md', 'docs/desktop-automation.zh-CN.md',
        'docs/native-automation-examples.md', 'docs/native-automation-examples.zh-CN.md',
    }
    return sorted(p for p in names if p.endswith('.md') and (
        p in ('README.md', 'README.zh-CN.md', 'CONTRIBUTING.md', 'CONTRIBUTING.zh-CN.md')
        or p.startswith(('docs/', 'acceptance/')) and not p.startswith('docs/research/')
        or p in ('capcut-cli/README.md', 'axure-cli/README.md', 'shapr3d-cli/README.md')
    ))


def route(source):
    if source == 'README.md':
        return 'index.html'
    if source == 'README.zh-CN.md':
        return 'zh/index.html'
    return source[:-3] + '.html'


def text_content(value):
    return html.unescape(re.sub(r'<[^>]+>', '', value)).strip()


class Rewriter(HTMLParser):
    def __init__(self, source, mapping, prefix, assets):
        super().__init__(convert_charrefs=False)
        self.source, self.mapping, self.prefix = source, mapping, prefix
        self.assets = assets
        self.output = []

    def link(self, value, image=False):
        parts = urlsplit(value)
        if parts.scheme or parts.netloc or not parts.path:
            return value
        target = posixpath.normpath(posixpath.join(posixpath.dirname(self.source), unquote(parts.path)))
        if image and target == 'capcut-cli/assets/capcut-cli-teaser.gif':
            target = 'capcut-cli/assets/capcut-cli-demo.jpg'
        if image and target in self.assets:
            url = self.prefix + target
        elif target in self.mapping:
            url = self.prefix + self.mapping[target]
        else:
            url = (RAW if image or target.endswith(('.mp4', '.gif', '.jpg', '.png')) else REPO + '/blob/main/') + quote(target, safe='/')
        return url + ('?' + parts.query if parts.query else '') + ('#' + parts.fragment if parts.fragment else '')

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.output.append('<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable table">')
        attrs = [(k, self.link(v, tag == 'img') if k in ('href', 'src') and v else v) for k, v in attrs]
        if tag == 'img':
            attrs += [('loading', 'lazy'), ('decoding', 'async')]
        self.output.append('<' + tag + ''.join(' ' + k + ('="' + html.escape(v, quote=True) + '"' if v is not None else '') for k, v in attrs) + '>')

    def handle_endtag(self, tag):
        self.output.append('</' + tag + '>')
        if tag == 'table':
            self.output.append('</div>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        self.output.append(data)

    def handle_entityref(self, name):
        self.output.append('&' + name + ';')

    def handle_charref(self, name):
        self.output.append('&#' + name + ';')


def build(base_url, output):
    parsed = urlsplit(base_url)
    if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('base-url must be an absolute HTTP(S) URL without query or fragment')
    base_url = base_url.rstrip('/') + '/'
    prefix = urlsplit(base_url).path
    output.mkdir(parents=True, exist_ok=True)
    mapping = {p: route(p) for p in sources()}
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    assets = {p for p in tracked if re.fullmatch(r'(capcut|axure|shapr3d)-cli/assets/[^/]+\.(jpg|png)', p)}
    for asset in assets:
        target = output / asset
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / asset, target)
    urls = []
    verification = json.loads((ROOT / 'site/verification.json').read_text(encoding='utf-8'))
    verification_tags = ''.join(
        f'<meta name="{html.escape(name, quote=True)}" content="{html.escape(value, quote=True)}">'
        for name, value in verification.items()
        if name in ('google-site-verification', 'msvalidate.01')
    )
    for source, destination in mapping.items():
        zh = '.zh-CN.md' in source or source in ('capcut-cli/README.md', 'axure-cli/README.md', 'shapr3d-cli/README.md')
        lang = 'zh-CN' if zh else 'en'
        md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc'], extension_configs={'toc': {'slugify': slug, 'permalink': '#'}})
        body = md.convert((ROOT / source).read_text(encoding='utf-8'))
        heading = text_content(re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S).group(1)).rstrip('#')
        title = heading if source.startswith('README') else heading + ' | reverse-cli-anything'
        if source == 'README.md':
            title = 'reverse-cli-anything — Closed-source software automation for AI agents'
        elif source == 'README.zh-CN.md':
            title = 'reverse-cli-anything — AI Agent 闭源软件自动化与 CLI 逆向工具链'
        paragraphs = re.findall(r'<p>(.*?)</p>', body, re.S)
        description = next((text_content(p) for p in paragraphs
                            if len(text_content(re.sub(r'<a\b[^>]*>.*?</a>', '', p, flags=re.S))) > 65), heading)
        description = description[:157].rsplit(' ', 1)[0] + '…' if len(description) > 160 else description
        rewrite = Rewriter(source, mapping, prefix, assets)
        rewrite.feed(body)
        canonical = base_url + ('' if destination == 'index.html' else destination.replace('/index.html', '/'))
        urls.append(canonical)
        counterpart = source.replace('.zh-CN.md', '.md') if '.zh-CN.md' in source else source[:-3] + '.zh-CN.md'
        alternate = ''
        language_link = ''
        if counterpart in mapping:
            en_src, zh_src = (counterpart, source) if zh else (source, counterpart)
            for code, src in [('en', en_src), ('zh-CN', zh_src), ('x-default', en_src)]:
                path = mapping[src]
                url = base_url + ('' if path == 'index.html' else path.replace('/index.html', '/'))
                alternate += f'<link rel="alternate" hreflang="{code}" href="{html.escape(url)}">'
            language_link = f'<a href="{prefix}{mapping[counterpart]}" lang="{"en" if zh else "zh-CN"}">{"English" if zh else "中文"}</a>'
        suffix = '.zh-CN' if zh else ''
        home = prefix + ('zh/' if zh else '')
        nav = [(home, '项目介绍' if zh else 'Overview'), (prefix + f'docs/install{suffix}.html', '安装指南' if zh else 'Installation'), (prefix + f'docs/faq{suffix}.html', '常见问题' if zh else 'FAQ'), (prefix + f'docs/HARNESS{suffix}.html', '工程手册' if zh else 'Engineering manual'), (prefix + f'docs/runtime{suffix}.html', '命令参考' if zh else 'Command reference'), (prefix + f'acceptance/README{suffix}.html', '验收标准' if zh else 'Verification')]
        navigation = ''.join(f'<a href="{url}">{label}</a>' for url, label in nav)
        navigation += f'<a href="{prefix}docs/desktop-automation{suffix}.html">{"自动化选型" if zh else "Automation guide"}</a><a href="{prefix}docs/native-automation-examples{suffix}.html">{"原生案例与证据" if zh else "Native examples"}</a>'
        schema = {'@context': 'https://schema.org', '@type': 'TechArticle', 'headline': title, 'description': description, 'url': canonical, 'inLanguage': lang, 'isPartOf': {'@type': 'WebSite', 'name': 'reverse-cli-anything', 'url': base_url}}
        if source.startswith('README'):
            schema = {'@context': 'https://schema.org', '@type': 'SoftwareSourceCode', 'name': 'reverse-cli-anything', 'description': description, 'url': canonical, 'codeRepository': REPO, 'license': REPO + '/blob/main/LICENSE', 'programmingLanguage': 'Python', 'inLanguage': lang}
        escaped = html.escape
        page = f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escaped(title)}</title><meta name="description" content="{escaped(description, quote=True)}">{verification_tags if source == 'README.md' else ''}
<link rel="canonical" href="{escaped(canonical)}">{alternate}
<meta property="og:type" content="website"><meta property="og:site_name" content="reverse-cli-anything">
<meta property="og:title" content="{escaped(title)}"><meta property="og:description" content="{escaped(description)}"><meta property="og:url" content="{escaped(canonical)}">
<meta property="og:image" content="{base_url}capcut-cli/assets/capcut-cli-demo.jpg"><meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="{prefix}site.css"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace('<', chr(92) + 'u003c')}</script></head>
<body><a class="skip" href="#content">{'跳至正文' if zh else 'Skip to content'}</a>
<header class="top"><a class="brand" href="{home}">reverse-cli-anything<span aria-hidden="true"> ↗</span></a><nav aria-label="Primary">{language_link}<a href="{prefix}docs/faq{suffix}.html">FAQ</a><a href="{REPO}">GitHub ↗</a></nav></header>
<div class="shell"><aside><nav aria-label="Documentation"><strong>{'文档' if zh else 'Documentation'}</strong>{navigation}</nav></aside>
<main id="content"><div class="eyebrow">{'开源 · 逆向工程 · Agent 工具' if zh else 'Open source / Reverse engineering / Agent tools'}</div>{''.join(rewrite.output)}
<p class="source"><a href="{REPO}/blob/main/{quote(source, safe='/')}">{'在 GitHub 查看本页源文档' if zh else 'View this page source on GitHub'}</a></p></main></div>
<footer>reverse-cli-anything · <a href="{REPO}/blob/main/LICENSE">MIT</a> · {'以实际应用验证为依据' if zh else 'Grounded in real application verification'}</footer><script src="{prefix}site.js" defer></script></body></html>'''
        target = output / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding='utf-8')
    shutil.copyfile(ROOT / 'site/site.css', output / 'site.css')
    shutil.copyfile(ROOT / 'site/site.js', output / 'site.js')
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    sitemap = ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
    for url in urls:
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = url
    ET.ElementTree(sitemap).write(output / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    (output / '.nojekyll').write_text('', encoding='utf-8')
    (output / '404.html').write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="robots" content="noindex"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found</title><link rel="stylesheet" href="{prefix}site.css"><main class="shell"><div><h1>Page not found</h1><p><a href="{prefix}">Return to the documentation</a></p></div></main></html>', encoding='utf-8')
    # Project sites cannot control github.io's root robots.txt. Emit only at a domain root.
    if prefix == '/':
        (output / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + base_url + 'sitemap.xml\n', encoding='utf-8')
    elif (output / 'robots.txt').exists():
        (output / 'robots.txt').unlink()
    print(json.dumps({'pages': len(mapping), 'output': str(output), 'base_url': base_url}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=DEFAULT_URL)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/site')
    args = parser.parse_args()
    build(args.base_url, args.output.resolve())
