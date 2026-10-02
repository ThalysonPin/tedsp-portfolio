"""Publish selected issues as static portfolio content. Uses Python's standard library."""
import argparse
import base64
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
MAX_IMAGE_BYTES = 12 * 1024 * 1024


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != 'https' or not github_image_host(parsed.hostname):
            raise ValueError('Image redirected outside GitHub')
        # Authorization is an unredirected header: never forward it to a CDN.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def github_image_host(host):
    return host in {'github.com', 'api.github.com', 'githubusercontent.com'} or bool(host and host.endswith('.githubusercontent.com'))


def request_bytes(url, token='', accept='application/vnd.github.full+json'):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not github_image_host(parsed.hostname):
        raise ValueError('Only HTTPS GitHub URLs can be downloaded')
    req = Request(url, headers={'User-Agent': 'TEDSP-Portfolio', 'Accept': accept, 'X-GitHub-Api-Version': '2022-11-28'})
    if token and parsed.hostname in {'api.github.com', 'github.com'}:
        req.add_unredirected_header('Authorization', 'Bearer ' + token)
    with build_opener(SafeRedirect()).open(req, timeout=30) as response:
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError('GitHub response exceeded the size limit')
    return data


def get_json(url, token):
    return json.loads(request_bytes(url, token))


def fetch_issues(repo, token, label=''):
    result = []
    page = 1
    while True:
        params = {'state': 'all', 'per_page': 100, 'page': page, 'sort': 'updated', 'direction': 'desc'}
        if label:
            params['labels'] = label
        batch = get_json('https://api.github.com/repos/' + repo + '/issues?' + urlencode(params), token)
        if not isinstance(batch, list):
            raise ValueError('Unexpected issues API response')
        result.extend(item for item in batch if 'pull_request' not in item)
        if len(batch) < 100:
            return result
        page += 1


def image_extension(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if data.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return '.gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return '.webp'
    raise ValueError('Only PNG, JPEG, GIF and WebP images are published')


class ImageStore:
    def __init__(self, repo, output, token='', offline=False):
        self.repo, self.output, self.token, self.offline = repo, Path(output), token, offline
        self.directory = self.output / 'issue-media'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.cache = {}

    def save(self, source):
        source = html.unescape(source)
        if source in self.cache:
            return self.cache[source]
        parsed = urlparse(source)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port or not github_image_host(parsed.hostname):
            return None
        name = hashlib.sha256(source.encode()).hexdigest()[:20]
        existing = list(self.directory.glob(name + '.*'))
        if existing and self.offline:
            path = existing[0]
            image_extension(path.read_bytes())
        else:
            parts = unquote(parsed.path).strip('/').split('/')
            repo_parts = self.repo.split('/')
            repository_image = parsed.hostname == 'github.com' and parts[:2] == repo_parts and len(parts) >= 5 and parts[2] in {'blob', 'raw'}
            if repository_image:
                ref, file_path = parts[3], '/'.join(parts[4:])
                if any(part in {'..', '.'} for part in file_path.split('/')):
                    return None
                local_path = ROOT / file_path
                if self.offline and local_path.is_file():
                    data = local_path.read_bytes()
                elif self.offline:
                    raise ValueError('Missing local image: ' + file_path)
                else:
                    endpoint = 'https://api.github.com/repos/' + self.repo + '/contents/' + quote(file_path, safe='/') + '?' + urlencode({'ref': ref})
                    blob = get_json(endpoint, self.token)
                    if blob.get('encoding') != 'base64':
                        raise ValueError('Image content unavailable from GitHub')
                    data = base64.b64decode(blob['content'])
            elif self.offline:
                raise ValueError('Offline image not cached: ' + parsed.path)
            else:
                data = request_bytes(source, self.token, 'application/octet-stream')
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError('Image exceeded the size limit')
            path = self.directory / (name + image_extension(data))
            path.write_bytes(data)
        result = 'issue-media/' + path.name
        self.cache[source] = result
        return result


def safe_link(value):
    parsed = urlparse(html.unescape(value))
    return value if parsed.scheme in {'https', 'mailto'} and not parsed.username and not parsed.password else None


class IssueHTML(HTMLParser):
    """Keep document markup only; rewrite images to static, local assets."""
    ALLOWED = {'p', 'strong', 'em', 'del', 'code', 'pre', 'blockquote', 'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'br', 'details', 'summary'}
    BLOCKED = {'script', 'style', 'iframe', 'object', 'svg', 'form', 'video', 'audio'}

    def __init__(self, images):
        super().__init__(convert_charrefs=True)
        self.images = images
        self.output = []
        self.stack = []
        self.blocked = 0
        self.pictures = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKED:
            self.blocked += 1
        if self.blocked:
            return
        attrs = dict(attrs)
        if tag == 'input':
            if attrs.get('type') == 'checkbox':
                self.output.append('☑ ' if 'checked' in attrs else '☐ ')
            return
        if tag == 'img':
            path = self.images.save(attrs.get('src', ''))
            alt = html.escape(attrs.get('alt', 'Imagem do projeto'), quote=True)
            if path:
                self.output.append(f'<img src="{path}" alt="{alt}" loading="lazy" decoding="async">')
                if path not in self.pictures:
                    self.pictures.append(path)
            return
        mapped = 'h' + str(max(3, min(int(tag[1]) + 1, 6))) if re.fullmatch(r'h[1-6]', tag) else tag
        extra = ''
        if tag == 'a':
            link = safe_link(attrs.get('href', ''))
            if link:
                extra = ' href="' + html.escape(link, quote=True) + '" target="_blank" rel="noopener noreferrer"'
            else:
                mapped = 'span'
        elif tag not in self.ALLOWED and not re.fullmatch(r'h[1-6]', tag):
            self.stack.append((tag, None))
            return
        self.output.append('<' + mapped + extra + '>')
        if tag not in {'hr', 'br'}:
            self.stack.append((tag, mapped))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in {'img', 'hr', 'br'}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.blocked:
            if tag in self.BLOCKED:
                self.blocked -= 1
            return
        if self.stack and self.stack[-1][0] == tag:
            _, mapped = self.stack.pop()
            if mapped:
                self.output.append('</' + mapped + '>')

    def handle_data(self, data):
        if not self.blocked:
            self.output.append(html.escape(data))


def markdown_fixture(source):
    """Small offline preview renderer. Production uses GitHub's rendered Markdown."""
    def inline(value):
        value = html.escape(value)
        value = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img alt="\1" src="\2">', value)
        value = re.sub(r'\[([^\]]*)\]\(([^)]+)\)', r'<a href="\2">\1</a>', value)
        value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
        return re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
    blocks, paragraph, listing = [], [], False
    def flush():
        if paragraph:
            blocks.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    for line in source.splitlines() + ['']:
        if not line.strip():
            flush()
            if listing:
                blocks.append('</ul>'); listing = False
        elif line.startswith('#'):
            flush()
            match = re.match(r'^(#{1,6})\s+(.+)', line)
            if match:
                level = len(match[1]); blocks.append(f'<h{level}>' + inline(match[2]) + f'</h{level}>')
        elif line.startswith('- '):
            flush()
            if not listing:
                blocks.append('<ul>'); listing = True
            blocks.append('<li>' + inline(line[2:]) + '</li>')
        elif line.strip().startswith('<img '):
            flush(); blocks.append(line)
        elif line.startswith('|'):
            flush()
            if not re.match(r'^\|[\s:|\-]+$', line):
                blocks.append('<table><tbody><tr>' + ''.join('<td>' + inline(cell.strip()) + '</td>' for cell in line.strip('|').split('|')) + '</tr></tbody></table>')
        else:
            paragraph.append(line.strip())
    return '\n'.join(blocks)


def summary(body):
    for paragraph in re.split(r'\n\s*\n', body or ''):
        paragraph = paragraph.strip()
        if not paragraph or paragraph.startswith(('#', '<', '![', '|', '- ')):
            continue
        plain = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', paragraph)
        plain = re.sub(r'[*`_]', '', plain)
        plain = re.sub(r'\s+', ' ', plain)
        return plain if len(plain) <= 270 else plain[:267].rsplit(' ', 1)[0] + '…'
    return ''


def build_feed(issues, repo, output, token='', label='', offline=False):
    images = ImageStore(repo, output, token, offline)
    projects = []
    for issue in sorted(issues, key=lambda i: (i.get('updated_at', ''), i.get('number', 0)), reverse=True):
        labels = [item['name'] if isinstance(item, dict) else item for item in issue.get('labels', [])]
        if 'pull_request' in issue or (label and label not in labels):
            continue
        raw = issue.get('body') or ''
        rendered = issue.get('body_html')
        if rendered is None and not offline:
            raise ValueError('GitHub did not return rendered Markdown')
        parser = IssueHTML(images)
        parser.feed(rendered if rendered is not None else markdown_fixture(raw))
        parser.close()
        projects.append({'number': issue['number'], 'title': issue['title'], 'summary': summary(raw), 'updatedAt': issue.get('updated_at', ''), 'url': 'https://github.com/' + repo + '/issues/' + str(issue['number']), 'labels': [name for name in labels if name != label], 'bodyHtml': ''.join(parser.output), 'images': parser.pictures})
    feed = {'repository': repo, 'projects': projects}
    encoded = json.dumps(feed, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    Path(output).mkdir(parents=True, exist_ok=True)
    (Path(output) / 'issue-projects.js').write_text('window.PORTFOLIO_ISSUES = ' + encoded + ';\n', encoding='utf-8')
    active = {Path(path).name for project in projects for path in project['images']}
    for path in images.directory.iterdir():
        if path.name not in active and path.is_file():
            path.unlink()
    return feed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'ThalysonPin/tedsp-portfolio'))
    parser.add_argument('--label', default='', help='Optional label filter; by default publish every issue')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--fixture', type=Path, help='Offline preview from an API JSON fixture')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        parser.error('Invalid repository name')
    token = os.environ.get('GITHUB_TOKEN', '')
    if not args.fixture and not token:
        parser.error('GITHUB_TOKEN is required to synchronize private issues')
    issues = json.loads(args.fixture.read_text()) if args.fixture else fetch_issues(args.repository, token, args.label)
    feed = build_feed(issues, args.repository, args.output, token, args.label, bool(args.fixture))
    print('Synchronized', len(feed['projects']), 'portfolio project(s) and', sum(len(p['images']) for p in feed['projects']), 'image(s).')


if __name__ == '__main__':
    main()
