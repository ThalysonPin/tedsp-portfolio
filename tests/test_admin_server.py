"""HTTP integration tests for authentication, content isolation and persistence."""
from copy import deepcopy
import http.client
import json
from pathlib import Path
import shutil
import struct
import tempfile
import threading
import time
import unittest
import zlib

from server.admin_server import Config, Store, create_server, reset_password


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'test-admin-password-2026!'
TOKEN = 'integration-test-setup-token-32-characters-minimum'
EMAIL = 'thalysonemanuels.p@gmail.com'


def tiny_png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff')) + chunk(b'IEND', b'')


class AdminServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.static, self.data_dir = root / 'dist', root / 'private'
        self.static.mkdir()
        (self.static / 'admin').mkdir()
        shutil.copyfile(ROOT / 'dist/content.json', self.static / 'content.json')
        (self.static / 'index.html').write_text('<h1>Portfolio</h1>')
        (self.static / 'admin/index.html').write_text('<h1>Admin</h1>')
        (self.static / 'issue-projects.js').write_text('window.PORTFOLIO_ISSUES = {"projects":[{"number":1,"title":"Original GitHub issue"}]};')
        self.config = Config(data_dir=self.data_dir, static_dir=self.static, setup_token=TOKEN, port=0)
        self.server = create_server(self.config, host='127.0.0.1', port=0)
        self.config.public_origin = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.server.RequestHandlerClass.log_message = lambda *args: None
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.cookie, self.csrf = '', ''

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, body=None, *, headers=None, auth=True, origin=True, csrf=True):
        supplied = dict(headers or {})
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
            supplied.setdefault('Content-Type', 'application/json')
        if method not in ('GET', 'HEAD'):
            if origin:
                supplied.setdefault('Origin', self.config.public_origin)
            if csrf and self.csrf:
                supplied.setdefault('X-CSRF-Token', self.csrf)
        if auth and self.cookie:
            supplied.setdefault('Cookie', self.cookie)
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=5)
        try:
            connection.request(method, path, body=body, headers=supplied)
            response = connection.getresponse()
            raw, response_headers = response.read(), dict(response.getheaders())
            data = json.loads(raw) if response_headers.get('Content-Type', '').startswith('application/json') and raw else raw
            return response.status, data, response_headers
        finally:
            connection.close()

    def setup_admin(self):
        status, data, headers = self.request('POST', '/api/admin/setup', {'email': EMAIL, 'password': PASSWORD, 'token': TOKEN})
        self.assertEqual(status, 200, data)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.csrf = data['csrf']
        return data, headers

    def login(self, password=PASSWORD):
        status, data, headers = self.request('POST', '/api/admin/login', {'email': EMAIL, 'password': password}, auth=False)
        if status == 200:
            self.cookie = headers['Set-Cookie'].split(';')[0]
            self.csrf = data['csrf']
        return status, data, headers

    def test_initial_setup_needs_private_token_and_is_one_time(self):
        status, state, _ = self.request('GET', '/api/admin/session')
        self.assertEqual(status, 200)
        self.assertTrue(state['setupRequired'])
        self.assertTrue(state['setupAvailable'])
        self.assertFalse(state['authenticated'])
        self.assertNotIn('csrf', state)
        status, _, _ = self.request('POST', '/api/admin/setup', {'email': EMAIL, 'password': PASSWORD, 'token': 'wrong'})
        self.assertEqual(status, 401)
        data, headers = self.setup_admin()
        self.assertTrue(data['authenticated'])
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.assertNotIn('Secure', headers['Set-Cookie'])
        self.assertEqual(self.request('POST', '/api/admin/setup', {'email': EMAIL, 'password': PASSWORD, 'token': TOKEN})[0], 409)
        with self.server.store.db() as db:
            stored = db.execute('SELECT password FROM admin').fetchone()[0]
            self.assertTrue(stored.startswith('scrypt$'))
            self.assertNotIn(PASSWORD, stored)
            digest = db.execute('SELECT token_hash FROM sessions').fetchone()[0]
            self.assertNotEqual(digest, self.cookie.split('=', 1)[1])

    def test_setup_fails_closed_without_strong_configured_token(self):
        self.config.setup_token = ''
        self.assertFalse(self.request('GET', '/api/admin/session')[1]['setupAvailable'])
        self.assertEqual(self.request('POST', '/api/admin/setup', {'email': EMAIL, 'password': PASSWORD, 'token': ''})[0], 503)
        self.assertFalse(self.server.store.has_admin())

    def test_simultaneous_setup_creates_only_one_admin(self):
        from concurrent.futures import ThreadPoolExecutor
        body = {'email': EMAIL, 'password': PASSWORD, 'token': TOKEN}
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(pool.map(lambda _: self.request('POST', '/api/admin/setup', body)[0], range(2)))
        self.assertEqual(statuses, [200, 409])
        with self.server.store.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin').fetchone()[0], 1)

    def test_setup_and_login_reject_external_and_missing_origin(self):
        request = {'email': EMAIL, 'password': PASSWORD, 'token': TOKEN}
        self.assertEqual(self.request('POST', '/api/admin/setup', request, origin=False)[0], 403)
        self.assertEqual(self.request('POST', '/api/admin/setup', request, headers={'Origin': 'https://evil.example'})[0], 403)
        self.setup_admin()
        self.assertEqual(self.request('POST', '/api/admin/login', request, headers={'Origin': 'https://evil.example'})[0], 403)

    def test_https_origin_sets_secure_cookie(self):
        self.config.public_origin = 'https://tedsptech.com'
        _, headers = self.setup_admin()
        self.assertIn('; Secure', headers['Set-Cookie'])

    def test_admin_routes_are_protected_and_session_expires(self):
        for method, path in [('GET', '/api/admin/content'), ('GET', '/api/admin/issue-projects'), ('PUT', '/api/admin/content'), ('POST', '/api/admin/upload?kind=photo')]:
            self.assertEqual(self.request(method, path, {}, auth=False)[0], 401)
        self.setup_admin()
        with self.server.store.db() as db:
            db.execute('UPDATE sessions SET expires=?', (int(time.time()) - 1,))
        self.assertEqual(self.request('GET', '/api/admin/content')[0], 401)

    def test_mutations_require_csrf_and_same_origin(self):
        self.setup_admin()
        self.assertEqual(self.request('POST', '/api/admin/logout', {}, csrf=False)[0], 403)
        self.assertEqual(self.request('POST', '/api/admin/logout', {}, headers={'X-CSRF-Token': 'x' * 43})[0], 403)
        self.assertEqual(self.request('POST', '/api/admin/logout', {}, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/api/admin/content')[0], 200)

    def test_login_rate_limit_persists_in_sqlite(self):
        self.setup_admin()
        for _ in range(8):
            self.assertEqual(self.login('incorrect password')[0], 401)
        self.assertEqual(self.login()[0], 429)
        reloaded = Store(self.config)
        with reloaded.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0], 8)

    def test_save_is_public_atomic_conflict_checked_and_persistent(self):
        self.setup_admin()
        _, original, _ = self.request('GET', '/api/admin/content')
        changed = deepcopy(original['content'])
        changed['text']['pt']['heroIntro'] = 'Texto atualizado no painel.'
        changed['jobs'] = changed['jobs'][:-1]
        changed['projects'] = []
        changed['theme']['light']['accent'] = '#123456'
        changed['hiddenIssues'] = [1]
        changed['customIssues'] = [{'number': 1000001, 'url': '', 'translations': {lang: {'title': 'Novo projeto', 'summary': 'Resumo', 'bodyText': 'Documentação em texto.', 'images': []} for lang in ('pt', 'en')}}]
        status, saved, _ = self.request('PUT', '/api/admin/content', {'content': changed, 'revision': original['revision']})
        self.assertEqual(status, 200, saved)
        self.assertEqual(saved['revision'], original['revision'] + 1)
        self.assertEqual(self.request('GET', '/api/site', auth=False)[1], saved)
        self.assertEqual(Store(self.config).content(), saved)
        status, _, _ = self.request('PUT', '/api/admin/content', {'content': changed, 'revision': original['revision']})
        self.assertEqual(status, 409)
        status, script, headers = self.request('GET', '/site-content.js', auth=False)
        self.assertEqual(status, 200)
        self.assertIn(b'window.PORTFOLIO_CONTENT = ', script)
        self.assertNotIn(TOKEN.encode(), script)
        self.assertNotIn(PASSWORD.encode(), script)
        self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_inline_markup_is_sanitized_and_other_html_rejected(self):
        self.setup_admin()
        _, current, _ = self.request('GET', '/api/admin/content')
        current['content']['text']['pt']['heroIntro'] = '<em onclick="alert(1)">Olá</em><img src=x onerror=alert(1)><br>Texto'
        status, saved, _ = self.request('PUT', '/api/admin/content', current)
        self.assertEqual(status, 200, saved)
        value = saved['content']['text']['pt']['heroIntro']
        self.assertEqual(value, '<em>Olá</em><br>Texto')
        saved['content']['jobs'][0]['description']['pt'] = '<img src=x onerror=alert(1)>'
        self.assertEqual(self.request('PUT', '/api/admin/content', saved)[0], 400)

    def test_content_rejects_unsafe_urls_colors_and_issue_html(self):
        self.setup_admin()
        _, original, _ = self.request('GET', '/api/admin/content')
        for section, key, value in [('profile', 'github', 'javascript:alert(1)'), ('profile', 'photo', 'https://evil.example/image.svg')]:
            changed = deepcopy(original)
            changed['content'][section][key] = value
            self.assertEqual(self.request('PUT', '/api/admin/content', changed)[0], 400)
        changed = deepcopy(original)
        changed['content']['theme']['light']['accent'] = 'red; background:url(https://evil.example)'
        self.assertEqual(self.request('PUT', '/api/admin/content', changed)[0], 400)
        changed = deepcopy(original)
        changed['content']['issueOverrides'] = {'1': {'translations': {'pt': {'bodyHtml': '<script>alert(1)</script>'}}}}
        self.assertEqual(self.request('PUT', '/api/admin/content', changed)[0], 400)
        changed = deepcopy(original)
        del changed['content']['text']['en']['heroRole']
        self.assertEqual(self.request('PUT', '/api/admin/content', changed)[0], 400)
        changed = deepcopy(original)
        changed['content']['theme']['default'] = 'system'
        self.assertEqual(self.request('PUT', '/api/admin/content', changed)[0], 400)

    def test_concurrent_login_attempts_cannot_bypass_limit(self):
        from concurrent.futures import ThreadPoolExecutor
        self.setup_admin()
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda _: self.request('POST', '/api/admin/login', {'email': EMAIL, 'password': 'wrong'}, auth=False)[0], range(12)))
        self.assertEqual(results.count(401), 8)
        self.assertEqual(results.count(429), 4)

    def test_upload_auth_magic_bytes_mime_and_persistence(self):
        self.setup_admin()
        headers = {'Content-Type': 'image/png'}
        status, uploaded, _ = self.request('POST', '/api/admin/upload?kind=photo', tiny_png(), headers=headers)
        self.assertEqual(status, 201, uploaded)
        self.assertRegex(uploaded['url'], r'^/uploads/[a-f0-9]{48}\.png$')
        status, body, response_headers = self.request('GET', uploaded['url'], auth=False)
        self.assertEqual(status, 200)
        self.assertEqual(body, tiny_png())
        self.assertEqual(response_headers['Content-Type'], 'image/png')
        self.assertEqual(response_headers['X-Content-Type-Options'], 'nosniff')
        self.assertTrue((Store(self.config).uploads / uploaded['url'].split('/')[-1]).exists())
        self.assertEqual(self.request('POST', '/api/admin/upload?kind=photo', b'<svg onload=alert(1)>', headers=headers)[0], 400)
        self.assertEqual(self.request('POST', '/api/admin/upload?kind=photo', tiny_png(), headers={'Content-Type': 'image/jpeg'})[0], 415)
        self.assertEqual(self.request('POST', '/api/admin/upload?kind=resume&lang=en', b'<html>fake pdf</html>', headers={'Content-Type': 'application/pdf'})[0], 415)
        pdf = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF'
        status, uploaded, _ = self.request('POST', '/api/admin/upload?kind=resume&lang=en', pdf, headers={'Content-Type': 'application/pdf'})
        self.assertEqual(status, 201, uploaded)
        status, body, headers = self.request('GET', uploaded['url'], auth=False)
        self.assertEqual(status, 200)
        self.assertEqual(body, pdf)
        self.assertIn('attachment;', headers['Content-Disposition'])

    def test_rejects_large_upload_before_reading_body(self):
        self.setup_admin()
        status, _, _ = self.request('POST', '/api/admin/upload?kind=photo', b'', headers={'Content-Length': str(5 * 1024 * 1024 + 1), 'Content-Type': 'image/png'})
        self.assertEqual(status, 413)

    def test_logout_and_password_change_revoke_sessions(self):
        self.setup_admin()
        old_cookie = self.cookie
        self.assertEqual(self.request('POST', '/api/admin/logout', {})[0], 200)
        self.assertEqual(self.request('GET', '/api/admin/content')[0], 401)
        self.assertEqual(self.login()[0], 200)
        second_cookie = self.cookie
        self.assertEqual(self.login()[0], 200)
        status, data, _ = self.request('POST', '/api/admin/password', {'currentPassword': PASSWORD, 'password': 'replacement-password-2026!'})
        self.assertEqual(status, 200, data)
        self.assertTrue(data['reauthenticate'])
        for cookie in (old_cookie, second_cookie, self.cookie):
            self.assertEqual(self.request('GET', '/api/admin/content', headers={'Cookie': cookie})[0], 401)
        self.assertEqual(self.login()[0], 401)
        self.assertEqual(self.login('replacement-password-2026!')[0], 200)

    def test_console_password_recovery_preserves_content(self):
        self.setup_admin()
        original = self.server.store.content()
        reset_password(self.config, 'new-console-password-2026!')
        self.assertEqual(self.request('GET', '/api/admin/content')[0], 401)
        self.assertEqual(self.server.store.content(), original)
        self.assertEqual(self.login('new-console-password-2026!')[0], 200)

    def test_static_paths_no_listing_traversal_database_or_symlink(self):
        self.assertEqual(self.request('GET', '/secret-admin')[0], 200)
        self.assertEqual(self.request('GET', '/healthz')[0], 200)
        for path in ('/data/portfolio.sqlite3', '/portfolio.sqlite3', '/%2e%2e/private/portfolio.sqlite3', '/admin/', '/.git/config', '/uploads/../../portfolio.sqlite3'):
            self.assertEqual(self.request('GET', path)[0], 404, path)
        (self.static / 'database-link').symlink_to(self.data_dir / 'portfolio.sqlite3')
        self.assertEqual(self.request('GET', '/database-link')[0], 404)

    def test_synced_projects_are_admin_read_only_source(self):
        self.setup_admin()
        status, data, _ = self.request('GET', '/api/admin/issue-projects')
        self.assertEqual(status, 200)
        self.assertEqual(data['projects'][0]['number'], 1)
        self.assertEqual(self.request('GET', '/api/admin/issue-projects', auth=False)[0], 401)


if __name__ == '__main__':
    unittest.main()
