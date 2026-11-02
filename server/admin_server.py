#!/usr/bin/env python3
"""Portfolio server and single-owner CMS. Runtime state belongs in DATA_DIR."""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
from html import escape
from html.parser import HTMLParser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
COOKIE = 'tedsp_admin'
SESSION_SECONDS = 8 * 60 * 60
JSON_LIMIT = 1024 * 1024
PHOTO_LIMIT = 5 * 1024 * 1024
PDF_LIMIT = 15 * 1024 * 1024
MAX_ATTEMPTS = 8
RATE_SECONDS = 600
EMAIL_RE = re.compile(r'^[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
UPLOAD_RE = re.compile(r'^/uploads/[a-f0-9]{48}\.(?:jpg|png|webp|pdf)$')
REQUIRED_TEXT_KEYS = frozenset('''issuesEyebrow issuesTitle issuesIntro issueRead issueUpdated issueDocument issueSource issueClose issueImages
skip menu navExperience navProjects navSkills navContact heroEyebrow heroRole heroIntro download viewProjects location english
metric1 metric2 metric3 experienceLabel experienceTitle experienceIntro projectsLabel projectsTitle projectsIntro githubIntro githubLink
skillsLabel skillsTitle skillsIntro educationLabel educationTitle educationSchool languageLabel languageTitle languageDescription
contactLabel contactTitle contactIntro copyEmail copied copyFailed footerResume backToTop caseLabel readCase flowLabel context role solution
result today moreCareer hideCareer metaDescription'''.split())


class APIError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


def fail(message: str):
    raise APIError(400, message)


class SafeInline(HTMLParser):
    """Allow only the formatting already used by the portfolio's labels."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.result, self.stack = [], []

    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self.result.append('<br>')
        elif tag in ('em', 'strong'):
            self.result.append(f'<{tag}>')
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self.result.append('<br>')

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack:
                current = self.stack.pop()
                self.result.append(f'</{current}>')
                if current == tag:
                    break

    def handle_data(self, data):
        self.result.append(escape(data, quote=False))

    def finish(self):
        self.close()
        while self.stack:
            self.result.append(f'</{self.stack.pop()}>')
        return ''.join(self.result)


def string(value, label='Texto', limit=30000, markup=False):
    if not isinstance(value, str) or len(value) > limit:
        fail(f'{label}: texto inválido ou longo demais.')
    if any(ord(c) < 32 and c not in '\t\r\n' for c in value):
        fail(f'{label}: caracteres de controle não são permitidos.')
    if markup:
        parser = SafeInline()
        parser.feed(value)
        return parser.finish()
    if re.search(r'<\s*[!/?A-Za-z]', value):
        fail(f'{label}: use texto simples, sem HTML.')
    return value


def obj(value, label, keys=None):
    if not isinstance(value, dict) or any(not isinstance(k, str) or k in ('__proto__', 'prototype', 'constructor') for k in value):
        fail(f'{label}: objeto inválido.')
    if keys is not None and set(value) - set(keys):
        fail(f'{label}: campos desconhecidos: {", ".join(sorted(set(value)-set(keys)))}.')
    return value


def sequence(value, label, limit=100):
    if not isinstance(value, list) or len(value) > limit:
        fail(f'{label}: lista inválida ou longa demais.')
    return value


def localized(value, label, lists=False):
    obj(value, label, ('pt', 'en'))
    if set(value) != {'pt', 'en'}:
        fail(f'{label}: preencha PT e EN.')
    if lists:
        return {lang: [string(s, label, 3000) for s in sequence(value[lang], label, 30)] for lang in ('pt', 'en')}
    return {lang: string(value[lang], label) for lang in ('pt', 'en')}


def plain_or_localized(value, label):
    return localized(value, label) if isinstance(value, dict) else string(value, label, 500)


def public_url(value, label, *, image=False, resume=False):
    value = string(value, label, 2000)
    if not value:
        return value
    if '\\' in value or any(c.isspace() for c in value) or '\x7f' in value:
        fail(f'{label}: URL inválida.')
    try:
        parsed = urlsplit(value)
        # Accessing port also rejects malformed authorities such as :invalid.
        parsed.port
    except ValueError:
        fail(f'{label}: URL inválida.')
    if parsed.scheme:
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            fail(f'{label}: use um endereço HTTP(S) válido.')
        if image or resume:
            fail(f'{label}: envie o arquivo pelo painel em vez de usar URL externa.')
        return value
    if parsed.netloc or parsed.fragment or '..' in unquote(parsed.path).split('/'):
        fail(f'{label}: caminho inválido.')
    if image:
        if value != 'portrait.jpg' and not (UPLOAD_RE.fullmatch(value) and value.endswith(('.png', '.jpg', '.webp'))):
            fail(f'{label}: selecione uma imagem enviada pelo painel.')
    elif resume:
        if not (re.fullmatch(r'curriculo-thalyson-(?:pt|en)\.pdf(?:\?v=[A-Za-z0-9-]+)?', value) or (UPLOAD_RE.fullmatch(value) and value.endswith('.pdf'))):
            fail(f'{label}: selecione um PDF enviado pelo painel.')
    elif not re.fullmatch(r'(?:/uploads/[a-f0-9]{48}\.(?:png|jpg|webp|pdf)|issue-media/[a-f0-9]{20}\.(?:png|jpg|gif|webp))', value):
        fail(f'{label}: caminho público inválido.')
    return value


def issue_copy(value, label, partial=False):
    allowed = ('title', 'summary', 'bodyText', 'images')
    obj(value, label, allowed)
    if not partial and not {'title', 'summary', 'bodyText'} <= set(value):
        fail(f'{label}: título, resumo e documentação são obrigatórios.')
    result = {key: string(value[key], label, 60000 if key == 'bodyText' else 5000) for key in ('title', 'summary', 'bodyText') if key in value}
    if 'images' in value:
        result['images'] = [public_url(path, label) for path in sequence(value['images'], label, 30)]
    return result


def issue(value, label, partial=False):
    obj(value, label, ('number', 'title', 'summary', 'bodyText', 'images', 'translations', 'labels', 'url', 'updatedAt'))
    result = issue_copy({k: v for k, v in value.items() if k in ('title', 'summary', 'bodyText', 'images')}, label, partial=True)
    if 'number' in value:
        n = value['number']
        if type(n) is not int or not 1 <= n <= 9007199254740991:
            fail(f'{label}: número inválido.')
        result['number'] = n
    if 'translations' in value:
        translations = obj(value['translations'], label, ('pt', 'en'))
        if not partial and set(translations) != {'pt', 'en'}:
            fail(f'{label}: adicione as versões PT e EN.')
        result['translations'] = {lang: issue_copy(copy, f'{label} {lang}', partial) for lang, copy in translations.items()}
    elif not partial:
        fail(f'{label}: adicione as versões PT e EN.')
    if 'labels' in value:
        result['labels'] = [string(x, label, 100) for x in sequence(value['labels'], label, 30)]
    if 'url' in value:
        result['url'] = public_url(value['url'], label)
    if 'updatedAt' in value:
        result['updatedAt'] = string(value['updatedAt'], label, 40)
    return result


def validate_content(value):
    fields = ('text', 'jobs', 'projects', 'skills', 'profile', 'theme', 'issueOverrides', 'hiddenIssues', 'customIssues')
    obj(value, 'Conteúdo', fields)
    if set(value) != set(fields):
        fail('Conteúdo incompleto: todas as seções são obrigatórias.')
    clean = {}
    obj(value['text'], 'Textos', ('pt', 'en'))
    if set(value['text']) != {'pt', 'en'}:
        fail('Textos: PT e EN são obrigatórios.')
    clean['text'] = {}
    for lang in ('pt', 'en'):
        entries = obj(value['text'][lang], 'Textos')
        if len(entries) > 300 or not entries:
            fail('Textos: quantidade de campos inválida.')
        if not REQUIRED_TEXT_KEYS <= set(entries):
            fail(f'Textos {lang}: campos obrigatórios ausentes: {", ".join(sorted(REQUIRED_TEXT_KEYS - set(entries)))}.')
        clean['text'][lang] = {string(k, 'Identificador', 100): string(v, f'Texto {k}', markup=True) for k, v in entries.items()}
    clean['jobs'] = []
    for row in sequence(value['jobs'], 'Experiências', 100):
        obj(row, 'Experiência', ('company', 'date', 'title', 'description', 'extra', 'tags'))
        if not {'company', 'date', 'title', 'description', 'tags'} <= set(row):
            fail('Experiência incompleta.')
        item = {'company': plain_or_localized(row['company'], 'Empresa')}
        item.update({k: localized(row[k], k) for k in ('date', 'title', 'description')})
        if 'extra' in row:
            item['extra'] = localized(row['extra'], 'Complemento')
        item['tags'] = [string(t, 'Tag', 100) for t in sequence(row['tags'], 'Tags', 30)]
        clean['jobs'].append(item)
    clean['projects'] = []
    ids = set()
    for row in sequence(value['projects'], 'Projetos', 100):
        obj(row, 'Projeto', ('id', 'number', 'tags', 'title', 'description', 'flow', 'details', 'url', 'image', 'imageAlt'))
        if not {'id', 'number', 'tags', 'title', 'description', 'flow', 'details'} <= set(row):
            fail('Projeto incompleto.')
        project_id = string(row['id'], 'ID', 80)
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', project_id) or project_id in ids:
            fail('Projeto: ID inválido ou repetido.')
        ids.add(project_id)
        item = {'id': project_id, 'number': string(row['number'], 'Número', 20), 'tags': [string(t, 'Tag', 100) for t in sequence(row['tags'], 'Tags', 30)]}
        item.update({k: localized(row[k], k) for k in ('title', 'description')})
        item['flow'] = localized(row['flow'], 'Etapas', lists=True)
        details = obj(row['details'], 'Detalhes', ('pt', 'en'))
        if set(details) != {'pt', 'en'}:
            fail('Detalhes: PT e EN são obrigatórios.')
        item['details'] = {}
        for lang in ('pt', 'en'):
            detail = obj(details[lang], 'Detalhes', ('context', 'role', 'solution', 'result'))
            if set(detail) != {'context', 'role', 'solution', 'result'}:
                fail('Detalhes incompletos.')
            item['details'][lang] = {k: string(v, 'Detalhes') for k, v in detail.items()}
        for key in ('url', 'image'):
            if key in row:
                item[key] = public_url(row[key], key, image=(key == 'image'))
        if 'imageAlt' in row:
            item['imageAlt'] = plain_or_localized(row['imageAlt'], 'Descrição da imagem')
        clean['projects'].append(item)
    clean['skills'] = []
    for row in sequence(value['skills'], 'Competências', 50):
        obj(row, 'Competência', ('title', 'items'))
        if set(row) != {'title', 'items'}:
            fail('Competência incompleta.')
        clean['skills'].append({'title': localized(row['title'], 'Competência'), 'items': [string(x, 'Competência', 200) for x in sequence(row['items'], 'Itens', 100)]})
    profile_keys = ('name', 'brand', 'brandMark', 'email', 'whatsapp', 'linkedin', 'github', 'photo', 'photoAlt', 'resume', 'metrics', 'footer')
    profile = obj(value['profile'], 'Perfil', profile_keys)
    if set(profile) != set(profile_keys):
        fail('Perfil incompleto.')
    p = {key: string(profile[key], key, 1000) for key in ('name', 'brand', 'brandMark', 'email', 'photoAlt', 'footer')}
    if not EMAIL_RE.fullmatch(p['email']) or len(p['email']) > 254:
        fail('E-mail inválido.')
    for key in ('whatsapp', 'linkedin', 'github'):
        p[key] = public_url(profile[key], key)
    p['photo'] = public_url(profile['photo'], 'Foto', image=True)
    resume = obj(profile['resume'], 'Currículo', ('pt', 'en'))
    if set(resume) != {'pt', 'en'}:
        fail('Currículos: PT e EN são obrigatórios.')
    p['resume'] = {lang: public_url(resume[lang], 'Currículo', resume=True) for lang in ('pt', 'en')}
    p['metrics'] = [string(x, 'Métrica', 100) for x in sequence(profile['metrics'], 'Métricas', 3)]
    if len(p['metrics']) != 3:
        fail('Preencha as três métricas.')
    clean['profile'] = p
    theme = obj(value['theme'], 'Tema', ('default', 'light', 'dark'))
    if set(theme) != {'default', 'light', 'dark'} or theme['default'] not in ('light', 'dark'):
        fail('Tema inválido.')
    clean['theme'] = {'default': theme['default']}
    for mode in ('light', 'dark'):
        entries = obj(theme[mode], 'Cores')
        if len(entries) > 100:
            fail('Cores demais.')
        for key, color in entries.items():
            if not re.fullmatch(r'[a-z][a-z0-9-]{0,79}', key) or not isinstance(color, str) or not re.fullmatch(r'#(?:[a-fA-F0-9]{3}|[a-fA-F0-9]{6}|[a-fA-F0-9]{8})', color):
                fail('Use apenas cores hexadecimais válidas.')
        clean['theme'][mode] = dict(entries)
    overrides = obj(value['issueOverrides'], 'Projetos sincronizados')
    if len(overrides) > 500:
        fail('Projetos sincronizados demais.')
    clean['issueOverrides'] = {}
    for key, row in overrides.items():
        if not re.fullmatch(r'[1-9][0-9]{0,15}', key) or int(key) > 9007199254740991:
            fail('Número da issue inválido.')
        item = issue(row, f'Issue {key}', partial=True)
        if 'number' in item and item['number'] != int(key):
            fail('Número da issue não corresponde ao identificador.')
        clean['issueOverrides'][key] = item
    hidden = sequence(value['hiddenIssues'], 'Issues ocultas', 500)
    if any(type(n) is not int or not 1 <= n <= 9007199254740991 for n in hidden):
        fail('Número de issue oculta inválido.')
    clean['hiddenIssues'] = list(dict.fromkeys(hidden))
    clean['customIssues'], ids = [], set()
    for row in sequence(value['customIssues'], 'Projetos autorais', 100):
        item = issue(row, 'Projeto autoral')
        number = item.get('number', 0)
        if number < 1000000 or number in ids:
            fail('Projetos autorais precisam de números únicos a partir de 1000000.')
        ids.add(number)
        clean['customIssues'].append(item)
    if len(json.dumps(clean, ensure_ascii=False).encode()) > JSON_LIMIT:
        fail('O conteúdo excede 1 MB.')
    return clean


def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()


def password_matches(password, encoded):
    try:
        _, salt, expected = encoded.split('$')
        digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=16384, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(digest, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def valid_password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 256:
        fail('A senha precisa ter de 12 a 256 caracteres.')
    return value


@dataclass
class Config:
    data_dir: Path
    static_dir: Path = ROOT / 'dist'
    public_origin: str = 'http://127.0.0.1:8080'
    admin_email: str = 'thalysonemanuels.p@gmail.com'
    setup_token: str = ''
    port: int = 8080

    @classmethod
    def from_env(cls):
        return cls(data_dir=Path(os.environ.get('DATA_DIR', '/data')), public_origin=os.environ.get('PUBLIC_ORIGIN', 'https://tedsptech.com').rstrip('/'),
                   admin_email=os.environ.get('ADMIN_EMAIL', 'thalysonemanuels.p@gmail.com').lower(), setup_token=os.environ.get('ADMIN_SETUP_TOKEN', ''),
                   port=int(os.environ.get('PORT', '8080')))

    def __post_init__(self):
        self.data_dir, self.static_dir = Path(self.data_dir), Path(self.static_dir)
        self.public_origin = self.public_origin.rstrip('/')
        origin = urlsplit(self.public_origin)
        if origin.scheme not in ('https', 'http') or not origin.hostname or origin.path or origin.query or origin.fragment or origin.username or origin.password:
            raise ValueError('PUBLIC_ORIGIN must be an exact HTTP(S) origin without a path.')
        if origin.scheme == 'http' and origin.hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('Use HTTPS in PUBLIC_ORIGIN outside localhost.')
        if not EMAIL_RE.fullmatch(self.admin_email):
            raise ValueError('Invalid ADMIN_EMAIL.')

    @property
    def secure(self):
        return self.public_origin.startswith('https://')


class Store:
    def __init__(self, config):
        self.config = config
        self.config.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.uploads = self.config.data_dir / 'uploads'
        self.uploads.mkdir(mode=0o700, exist_ok=True)
        self.path = self.config.data_dir / 'portfolio.sqlite3'
        with self.db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY CHECK(id=1), email TEXT NOT NULL, password TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, expires INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts (client TEXT NOT NULL, at INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS attempts_client ON attempts(client, at);
            ''')
            if not db.execute('SELECT 1 FROM content WHERE id=1').fetchone():
                seed = validate_content(json.loads((self.config.static_dir / 'content.json').read_text(encoding='utf-8')))
                db.execute('INSERT OR IGNORE INTO content VALUES (1, 1, ?)', (json.dumps(seed, ensure_ascii=False),))
        self.path.chmod(0o600)
        self.dummy_hash = password_hash(secrets.token_urlsafe(24))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def content(self):
        with self.db() as db:
            row = db.execute('SELECT revision,payload FROM content WHERE id=1').fetchone()
            return {'content': json.loads(row['payload']), 'revision': row['revision']}

    def update(self, content, revision):
        content = validate_content(content)
        if type(revision) is not int or revision < 1:
            fail('Revisão inválida.')
        with self.db() as db:
            cursor = db.execute('UPDATE content SET payload=?, revision=revision+1 WHERE id=1 AND revision=?', (json.dumps(content, ensure_ascii=False), revision))
            if cursor.rowcount != 1:
                raise APIError(409, 'O conteúdo mudou em outra sessão. Recarregue antes de salvar.')
        return {'content': content, 'revision': revision + 1}

    def has_admin(self):
        with self.db() as db:
            return bool(db.execute('SELECT 1 FROM admin WHERE id=1').fetchone())

    def rate_check(self, client):
        now = int(time.time())
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE at < ?', (now - RATE_SECONDS,))
            count = db.execute('SELECT COUNT(*) FROM attempts WHERE client=?', (client,)).fetchone()[0]
            if count >= MAX_ATTEMPTS:
                raise APIError(429, 'Muitas tentativas. Aguarde 10 minutos antes de tentar novamente.')
            db.execute('INSERT INTO attempts VALUES (?,?)', (client, now))

    def attempt(self, client, success=False):
        if success:
            with self.db() as db:
                db.execute('DELETE FROM attempts WHERE client=?', (client,))

    def session(self, token):
        if not token or not re.fullmatch(r'[A-Za-z0-9_-]{40,100}', token):
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.db() as db:
            db.execute('DELETE FROM sessions WHERE expires <= ?', (int(time.time()),))
            row = db.execute('SELECT csrf,expires FROM sessions WHERE token_hash=?', (digest,)).fetchone()
            admin = db.execute('SELECT email FROM admin WHERE id=1').fetchone()
            return dict(row, email=admin['email'], digest=digest) if row and admin else None

    def new_session(self):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('DELETE FROM sessions WHERE expires <= ?', (int(time.time()),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), csrf, int(time.time()) + SESSION_SECONDS))
        return token


def image_type(data):
    """Recognize supported containers and reject oversized image dimensions."""
    width = height = 0
    if len(data) >= 33 and data.startswith(b'\x89PNG\r\n\x1a\n') and data[12:16] == b'IHDR' and int.from_bytes(data[8:12], 'big') == 13:
        width, height = int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
        extension, mime = 'png', 'image/png'
    elif len(data) >= 20 and data[:3] == b'\xff\xd8\xff' and b'\xff\xd9' in data[-32:]:
        pos = 2
        while pos + 4 <= len(data):
            if data[pos] != 255:
                break
            marker = data[pos + 1]
            pos += 2
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            length = int.from_bytes(data[pos:pos + 2], 'big')
            if length < 2 or pos + length > len(data):
                break
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF) and length >= 8:
                height, width = int.from_bytes(data[pos + 3:pos + 5], 'big'), int.from_bytes(data[pos + 5:pos + 7], 'big')
                break
            pos += length
        extension, mime = 'jpg', 'image/jpeg'
    elif len(data) >= 30 and data[:4] == b'RIFF' and data[8:12] == b'WEBP' and int.from_bytes(data[4:8], 'little') + 8 == len(data):
        if data[12:16] == b'VP8X':
            width, height = int.from_bytes(data[24:27], 'little') + 1, int.from_bytes(data[27:30], 'little') + 1
        elif data[12:16] == b'VP8L' and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], 'little')
            width, height = (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        elif data[12:16] == b'VP8 ' and data[23:26] == b'\x9d\x01\x2a':
            width, height = int.from_bytes(data[26:28], 'little') & 0x3FFF, int.from_bytes(data[28:30], 'little') & 0x3FFF
        extension, mime = 'webp', 'image/webp'
    else:
        fail('Envie uma imagem PNG, JPEG ou WebP válida.')
    if not (1 <= width <= 12000 and 1 <= height <= 12000 and width * height <= 40000000):
        fail('Imagem inválida ou dimensões maiores que o limite de 40 megapixels.')
    return extension, mime


def create_server(config=None, host='0.0.0.0', port=None):
    config = config or Config.from_env()
    store = Store(config)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        server_version = 'Portfolio'
        sys_version = ''

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, format, *args):
            # URLs may contain setup tokens accidentally. Log paths without queries only.
            print(f'{self.address_string()} {self.command} {urlsplit(self.path).path}', flush=True)

        def respond(self, status, payload=b'', mime='application/json; charset=utf-8', extra=None):
            if not isinstance(payload, bytes):
                payload = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'same-origin')
            self.send_header('X-Frame-Options', 'SAMEORIGIN')
            if self.path.startswith(('/secret-admin', '/api/admin', '/admin/')):
                self.send_header('X-Robots-Tag', 'noindex, nofollow')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; font-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(payload)

        def request_origin(self):
            if self.headers.get('Origin') != config.public_origin:
                raise APIError(403, 'Origem da requisição não autorizada.')

        def token(self):
            try:
                cookies = SimpleCookie(self.headers.get('Cookie', ''))
                return cookies[COOKIE].value if COOKIE in cookies else ''
            except Exception:
                return ''

        def authenticated(self, mutate=False):
            session = store.session(self.token())
            if not session:
                raise APIError(401, 'Entre na sua conta para continuar.')
            if mutate:
                self.request_origin()
                candidate = self.headers.get('X-CSRF-Token', '')
                if not re.fullmatch(r'[A-Za-z0-9_-]{40,100}', candidate) or not hmac.compare_digest(candidate, session['csrf']):
                    raise APIError(403, 'Sessão inválida. Recarregue o painel e tente novamente.')
            return session

        def body(self, limit):
            if self.headers.get('Transfer-Encoding'):
                raise APIError(400, 'Use uma requisição com tamanho definido.')
            values = self.headers.get_all('Content-Length', [])
            if len(values) != 1 or not re.fullmatch(r'\d+', values[0]):
                raise APIError(411, 'Informe o tamanho da requisição.')
            size = int(values[0])
            if size > limit:
                raise APIError(413, 'Arquivo ou conteúdo maior que o limite permitido.')
            data = self.rfile.read(size)
            if len(data) != size:
                raise APIError(400, 'Requisição incompleta.')
            return data

        def json_body(self):
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise APIError(415, 'Use o formato JSON.')
            try:
                value = json.loads(self.body(JSON_LIMIT).decode('utf-8'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            except (ValueError, UnicodeError, RecursionError):
                fail('JSON inválido.')
            return obj(value, 'Requisição')

        def session_payload(self, session=None):
            exists = store.has_admin()
            return {'authenticated': bool(session), 'email': session['email'] if session else config.admin_email,
                    'setupRequired': not exists, 'setupAvailable': not exists and len(config.setup_token) >= 32,
                    **({'csrf': session['csrf']} if session else {})}

        def cookie(self, token='', expire=False):
            return f'{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={0 if expire else SESSION_SECONDS}' + ('; Secure' if config.secure else '')

        def serve_file(self, path, *, upload=False):
            if not path.is_file() or path.is_symlink():
                raise APIError(404, 'Arquivo não encontrado.')
            mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            extra = {}
            if path.suffix.lower() == '.pdf':
                mime = 'application/pdf'
                extra['Content-Disposition'] = f'attachment; filename="{path.name}"'
            self.respond(200, path.read_bytes(), mime, extra)

        def get(self):
            path = urlsplit(self.path).path
            if path == '/healthz':
                return self.respond(200, {'ok': True})
            if path == '/api/admin/session':
                return self.respond(200, self.session_payload(store.session(self.token())))
            if path in ('/api/site', '/api/admin/content'):
                if path.startswith('/api/admin/'):
                    self.authenticated()
                return self.respond(200, store.content())
            if path == '/site-content.js':
                payload = json.dumps(store.content()['content'], ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
                return self.respond(200, ('window.PORTFOLIO_CONTENT = ' + payload + ';\n').encode(), 'application/javascript; charset=utf-8')
            if path == '/api/admin/issue-projects':
                self.authenticated()
                source = (config.static_dir / 'issue-projects.js').read_text(encoding='utf-8')
                match = re.search(r'window\.PORTFOLIO_ISSUES\s*=\s*', source)
                if not match:
                    raise APIError(500, 'Não foi possível ler os projetos sincronizados.')
                feed = json.JSONDecoder().raw_decode(source[match.end():])[0]
                return self.respond(200, {'projects': feed.get('projects', [])})
            if path.startswith('/api/'):
                raise APIError(404, 'Rota não encontrada.')
            if path in ('/secret-admin', '/secret-admin/'):
                return self.serve_file(config.static_dir / 'admin' / 'index.html')
            if path.startswith('/uploads/'):
                if not UPLOAD_RE.fullmatch(path):
                    raise APIError(404, 'Arquivo não encontrado.')
                return self.serve_file(store.uploads / path.removeprefix('/uploads/'), upload=True)
            decoded = unquote(path)
            if '\\' in decoded or '\x00' in decoded or any(part.startswith('.') for part in decoded.split('/') if part):
                raise APIError(404, 'Arquivo não encontrado.')
            # Serve a fixed static root only; directory listing and traversal are disabled.
            candidate = (config.static_dir / (decoded.lstrip('/') or 'index.html')).resolve()
            if not candidate.is_relative_to(config.static_dir.resolve()):
                raise APIError(404, 'Arquivo não encontrado.')
            return self.serve_file(candidate)

        def mutate(self):
            path = urlsplit(self.path).path
            if path in ('/api/admin/setup', '/api/admin/login') and self.command == 'POST':
                self.request_origin()
                client = hashlib.sha256(self.client_address[0].encode()).hexdigest()
                store.rate_check(client)
                data = self.json_body()
                if path.endswith('/setup'):
                    if store.has_admin():
                        raise APIError(409, 'A conta já foi configurada. Faça login.')
                    if len(config.setup_token) < 32:
                        raise APIError(503, 'Configure um ADMIN_SETUP_TOKEN aleatório de pelo menos 32 caracteres no Coolify para definir a primeira senha.')
                    token = data.get('token', '')
                    email = data.get('email', '')
                    if not isinstance(token, str) or not isinstance(email, str) or len(token) > 512 or not hmac.compare_digest(token.encode(), config.setup_token.encode()) or email.lower() != config.admin_email:
                        store.attempt(client)
                        raise APIError(401, 'E-mail ou código de configuração incorreto.')
                    encoded = password_hash(valid_password(data.get('password')))
                    with store.db() as db:
                        try:
                            db.execute('INSERT INTO admin VALUES (1,?,?)', (config.admin_email, encoded))
                        except sqlite3.IntegrityError:
                            raise APIError(409, 'A conta já foi configurada. Faça login.')
                else:
                    password, email = data.get('password'), data.get('email')
                    with store.db() as db:
                        row = db.execute('SELECT email,password FROM admin WHERE id=1').fetchone()
                    candidate = password if isinstance(password, str) and len(password) <= 256 else ''
                    matched = password_matches(candidate, row['password'] if row else store.dummy_hash)
                    if not matched or not isinstance(email, str) or not row or email.lower() != row['email']:
                        store.attempt(client)
                        raise APIError(401, 'E-mail ou senha incorretos.')
                store.attempt(client, success=True)
                token = store.new_session()
                return self.respond(200, self.session_payload(store.session(token)), extra={'Set-Cookie': self.cookie(token)})
            session = self.authenticated(mutate=True)
            if path == '/api/admin/content' and self.command == 'PUT':
                data = self.json_body()
                return self.respond(200, store.update(data.get('content'), data.get('revision')))
            if path == '/api/admin/logout' and self.command == 'POST':
                self.body(JSON_LIMIT)
                with store.db() as db:
                    db.execute('DELETE FROM sessions WHERE token_hash=?', (session['digest'],))
                return self.respond(200, {'ok': True}, extra={'Set-Cookie': self.cookie(expire=True)})
            if path == '/api/admin/password' and self.command == 'POST':
                data = self.json_body()
                password = valid_password(data.get('password'))
                current = data.get('currentPassword', '')
                if not isinstance(current, str) or len(current) > 256:
                    fail('Senha atual inválida.')
                with store.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute('SELECT password FROM admin WHERE id=1').fetchone()
                    if not password_matches(current, row['password']):
                        raise APIError(401, 'Senha atual incorreta.')
                    db.execute('UPDATE admin SET password=? WHERE id=1', (password_hash(password),))
                    db.execute('DELETE FROM sessions')
                return self.respond(200, {'ok': True, 'reauthenticate': True}, extra={'Set-Cookie': self.cookie(expire=True)})
            if path == '/api/admin/upload' and self.command == 'POST':
                params = parse_qs(urlsplit(self.path).query)
                kind = params.get('kind', [''])[0]
                if kind not in ('photo', 'resume'):
                    fail('Tipo de arquivo inválido.')
                if kind == 'resume' and params.get('lang', [''])[0] not in ('pt', 'en'):
                    fail('Selecione PT ou EN para o currículo.')
                data = self.body(PHOTO_LIMIT if kind == 'photo' else PDF_LIMIT)
                content_type = self.headers.get('Content-Type', '').split(';')[0].strip()
                if kind == 'photo':
                    extension, mime = image_type(data)
                    if content_type != mime:
                        raise APIError(415, 'O formato informado não corresponde à imagem enviada.')
                else:
                    if content_type != 'application/pdf' or not re.match(br'%PDF-[12]\.[0-9]', data[:8]) or b'%%EOF' not in data[-2048:]:
                        raise APIError(415, 'Envie um arquivo PDF válido.')
                    extension = 'pdf'
                filename = secrets.token_hex(24) + '.' + extension
                target = store.uploads / filename
                with target.open('xb') as file:
                    file.write(data)
                    file.flush()
                    os.fsync(file.fileno())
                target.chmod(0o600)
                return self.respond(201, {'url': '/uploads/' + filename})
            raise APIError(404, 'Rota não encontrada.')

        def dispatch(self, mutate=False):
            try:
                self.mutate() if mutate else self.get()
            except APIError as error:
                # Close on errors so unread request bytes cannot become another request.
                self.close_connection = True
                self.respond(error.status, {'error': error.message}, extra={'Connection': 'close'})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                self.close_connection = True
            except Exception:
                self.close_connection = True
                self.respond(500, {'error': 'Não foi possível concluir a operação. Tente novamente.'}, extra={'Connection': 'close'})

        def do_GET(self):
            self.dispatch()

        def do_HEAD(self):
            self.dispatch()

        def do_POST(self):
            self.dispatch(mutate=True)

        def do_PUT(self):
            self.dispatch(mutate=True)

        def do_DELETE(self):
            self.dispatch(mutate=True)

    server = ThreadingHTTPServer((host, config.port if port is None else port), Handler)
    server.daemon_threads = True
    server.store, server.config = store, config
    return server


def reset_password(config, password):
    """Console-only recovery. Never expose this operation as a public endpoint."""
    encoded = password_hash(valid_password(password))
    store = Store(config)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM admin WHERE id=1').fetchone():
            raise APIError(409, 'Defina a primeira senha pelo painel antes de usar a recuperação.')
        db.execute('UPDATE admin SET password=? WHERE id=1', (encoded,))
        db.execute('DELETE FROM sessions')


def main():
    import argparse
    import getpass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', choices=['serve', 'reset-password'], default='serve')
    arguments = parser.parse_args()
    os.umask(0o077)
    if arguments.command == 'reset-password':
        password = getpass.getpass('Nova senha (mínimo 12 caracteres): ')
        confirmation = getpass.getpass('Confirme a nova senha: ')
        if password != confirmation:
            parser.exit(1, 'As senhas não correspondem.\n')
        try:
            reset_password(Config.from_env(), password)
        except APIError as error:
            parser.exit(1, error.message + '\n')
        print('Senha atualizada. Todas as sessões foram encerradas.')
        return
    server = create_server()
    print(f'Portfolio listening on port {server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
