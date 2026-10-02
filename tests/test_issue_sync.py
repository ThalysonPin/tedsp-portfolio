import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

SPEC = importlib.util.spec_from_file_location('sync', Path(__file__).parents[1] / 'scripts/sync_github_issues.py')
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def issue(number, labels=('portfolio',), **extra):
    return {'number': number, 'title': 'Projeto ' + str(number), 'body': 'Descrição do projeto.', 'body_html': '<h2>Contexto</h2><p>Descrição do projeto.</p>', 'updated_at': '2026-10-02T12:00:00Z', 'labels': [{'name': label} for label in labels], **extra}


class PublicationTests(unittest.TestCase):
    def test_only_selected_issues_are_published_including_closed_projects(self):
        with tempfile.TemporaryDirectory() as output:
            feed = sync.build_feed([issue(1, state='closed'), issue(2, labels=('bug',)), issue(3, pull_request={})], 'owner/repo', output, label='portfolio')
            self.assertEqual([p['number'] for p in feed['projects']], [1])
            self.assertEqual(feed['projects'][0]['url'], 'https://github.com/owner/repo/issues/1')

    def test_paginated_api_does_not_drop_projects_or_include_prs(self):
        first_page = [issue(i) for i in range(100)]
        second_page = [issue(101), issue(102, pull_request={})]
        with patch.object(sync, 'get_json', side_effect=[first_page, second_page]) as api:
            result = sync.fetch_issues('owner/repo', 'token', label='portfolio')
            self.assertEqual(len(result), 101)
            self.assertIn('page=2', api.call_args_list[1].args[0])
            self.assertIn('labels=portfolio', api.call_args_list[0].args[0])

    def test_issue_markup_cannot_execute_script_or_inject_attributes(self):
        dangerous = '<script>alert(1)</script><h1 onclick="evil()">Título</h1><p style="x">Texto</p><a href="javascript:evil()">Link</a><iframe src="https://evil.test"></iframe><img src="https://evil.test/tracker.png" onerror="evil()"><strong>Fim</strong>'
        with tempfile.TemporaryDirectory() as output:
            rendered = sync.build_feed([issue(1, body_html=dangerous)], 'owner/repo', output)['projects'][0]['bodyHtml']
            for forbidden in ['<script', '<iframe', 'onclick', 'onerror', 'javascript:', 'evil.test', 'style=']:
                self.assertNotIn(forbidden, rendered)
            self.assertIn('<h3>Título</h3>', rendered)
            self.assertIn('<strong>Fim</strong>', rendered)

    def test_feed_escapes_script_terminators_and_keeps_markup_inert(self):
        with tempfile.TemporaryDirectory() as output:
            sync.build_feed([issue(1, title='</script><script>evil()</script>')], 'owner/repo', output)
            source = (Path(output) / 'issue-projects.js').read_text()
            self.assertNotIn('</script>', source)
            payload = json.loads(source[len('window.PORTFOLIO_ISSUES = '):-2])
            self.assertEqual(payload['projects'][0]['title'], '</script><script>evil()</script>')

    def test_removed_label_removes_project_and_old_images(self):
        with tempfile.TemporaryDirectory() as output:
            image_dir = Path(output) / 'issue-media'
            image_dir.mkdir()
            stale = image_dir / 'old.png'
            stale.write_bytes(b'old')
            feed = sync.build_feed([issue(1, labels=())], 'owner/repo', output, label='portfolio')
            self.assertEqual(feed['projects'], [])
            self.assertFalse(stale.exists())

    def test_downloads_do_not_forward_credentials_to_image_cdn(self):
        request = Request('https://github.com/user-attachments/assets/example')
        request.add_unredirected_header('Authorization', 'Bearer secret')
        redirected = sync.SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'https://user-images.githubusercontent.com/image.png')
        self.assertIsNone(redirected.get_header('Authorization'))
        with self.assertRaises(ValueError):
            sync.SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'https://example.org/collect')

    def test_image_processing_localizes_private_repo_images_and_checks_file_type(self):
        url = 'https://github.com/owner/repo/blob/main/docs/image.png?raw=true'
        png = b'\x89PNG\r\n\x1a\nimage-data'
        with tempfile.TemporaryDirectory() as output, patch.object(sync, 'get_json', return_value={'encoding': 'base64', 'content': sync.base64.b64encode(png).decode()}):
            feed = sync.build_feed([issue(1, body_html=f'<p><img src="{url}" alt="Diagrama"></p>')], 'owner/repo', output)
            path = feed['projects'][0]['images'][0]
            self.assertTrue(path.startswith('issue-media/'))
            self.assertEqual((Path(output) / path).read_bytes(), png)
            self.assertNotIn('https://github.com', feed['projects'][0]['bodyHtml'])
        with self.assertRaises(ValueError):
            sync.image_extension(b'<svg onload="evil()"></svg>')

    def test_empty_issue_body_still_creates_readable_project(self):
        with tempfile.TemporaryDirectory() as output:
            feed = sync.build_feed([issue(1, body=None, body_html='')], 'owner/repo', output)
            self.assertEqual(len(feed['projects']), 1)
            self.assertEqual(feed['projects'][0]['summary'], '')

    def test_all_issues_are_published_by_default_without_requiring_a_label(self):
        with tempfile.TemporaryDirectory() as output:
            feed = sync.build_feed([issue(1, labels=()), issue(2, labels=('bug',), state='closed'), issue(3, pull_request={})], 'owner/repo', output)
            self.assertEqual([p['number'] for p in feed['projects']], [2, 1])
        with patch.object(sync, 'get_json', return_value=[]) as api:
            sync.fetch_issues('owner/repo', 'token')
            self.assertNotIn('labels=', api.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
