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


def bilingual_issue(number=1, pt_raw=None, en_raw=None, pt_html=None, en_html=None):
    pt_raw = pt_raw if pt_raw is not None else '# Meu projeto\n\n## Visão geral\n\nDesenvolvi a aplicação em React.'
    en_raw = en_raw if en_raw is not None else '# My project\n\n## Overview\n\nI built the application with React.'
    pt_html = pt_html if pt_html is not None else '<h1>Meu projeto</h1><h2>Visão geral</h2><p>Desenvolvi a aplicação em React.</p>'
    en_html = en_html if en_html is not None else '<h1>My project</h1><h2>Overview</h2><p>I built the application with React.</p>'
    raw = '<!-- portfolio:pt -->\n<details open>\n<summary>Português</summary>\n\n' + pt_raw + '\n</details>\n<!-- portfolio:en -->\n<details>\n<summary>English</summary>\n\n' + en_raw + '\n</details>\n<!-- /portfolio -->'
    rendered = '<details open><summary>Português</summary>' + pt_html + '</details><details><summary>English</summary>' + en_html + '</details>'
    return issue(number, body=raw, body_html=rendered)


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

    def test_bilingual_content_has_independent_titles_summaries_and_rich_html(self):
        project = bilingual_issue(pt_html='<div class="markdown-heading"><h1><strong>Meu projeto</strong></h1></div><h2>Visão geral</h2><p>Desenvolvi a <strong>aplicação</strong> em React.</p>')
        with tempfile.TemporaryDirectory() as output:
            published = sync.build_feed([project], 'owner/repo', output)['projects'][0]
            pt, en = published['translations']['pt'], published['translations']['en']
            self.assertEqual(pt['title'], 'Meu projeto')
            self.assertEqual(en['title'], 'My project')
            self.assertEqual(pt['summary'], 'Desenvolvi a aplicação em React.')
            self.assertEqual(en['summary'], 'I built the application with React.')
            self.assertIn('<strong>aplicação</strong>', pt['bodyHtml'])
            self.assertIn('<h3>Overview</h3>', en['bodyHtml'])
            self.assertNotIn('Meu projeto', pt['bodyHtml'])
            self.assertNotIn('My project', en['bodyHtml'])
            self.assertNotIn('Desenvolvi', en['bodyHtml'])
            self.assertEqual(published['title'], pt['title'])
            self.assertEqual(published['summary'], pt['summary'])
            self.assertEqual(published['bodyHtml'], pt['bodyHtml'])

    def test_both_language_blocks_are_sanitized_after_extraction(self):
        unsafe = '<h1>Title</h1><p onclick="evil()">Safe <strong>text</strong></p><script>evil()</script><a href="javascript:evil()">Unsafe</a><iframe src="https://evil.test"></iframe><img src="https://evil.test/pixel.png" onerror="evil()">'
        with tempfile.TemporaryDirectory() as output:
            project = sync.build_feed([bilingual_issue(pt_html=unsafe, en_html=unsafe)], 'owner/repo', output)['projects'][0]
            for language in ('pt', 'en'):
                rendered = project['translations'][language]['bodyHtml']
                self.assertIn('Safe <strong>text</strong>', rendered)
                for forbidden in ['onclick', '<script', '<iframe', 'javascript:', 'evil.test', 'onerror', 'evil()']:
                    self.assertNotIn(forbidden, rendered)

    def test_nested_details_and_tables_do_not_mix_languages(self):
        pt = '<h1>Meu projeto</h1><table><thead><tr><th>Camada</th></tr></thead><tbody><tr><td>Interface</td></tr></tbody></table><details><summary>English</summary><p>Detalhe interno em português.</p></details>'
        en = '<h1>My project</h1><details><summary>Implementation</summary><table><tr><td>Backend</td></tr></table><details><summary>Português</summary><p>Nested English content.</p></details></details>'
        with tempfile.TemporaryDirectory() as output:
            translations = sync.build_feed([bilingual_issue(pt_html=pt, en_html=en)], 'owner/repo', output)['projects'][0]['translations']
            self.assertIn('<table><thead><tr><th>Camada</th>', translations['pt']['bodyHtml'])
            self.assertIn('<summary>English</summary>', translations['pt']['bodyHtml'])
            self.assertNotIn('Nested English content.', translations['pt']['bodyHtml'])
            self.assertIn('<summary>Implementation</summary><table>', translations['en']['bodyHtml'])
            self.assertIn('Nested English content.', translations['en']['bodyHtml'])
            self.assertNotIn('Detalhe interno', translations['en']['bodyHtml'])

    def test_bilingual_image_cleanup_keeps_both_language_assets(self):
        pt_url = 'https://github.com/owner/repo/blob/main/docs/diagram-pt.png?raw=true'
        en_url = 'https://github.com/owner/repo/blob/main/docs/diagram-en.png?raw=true'
        pt = '<h1>Meu projeto</h1><p><img src="' + pt_url + '" alt="Diagrama em português"></p>'
        en = '<h1>My project</h1><p><img src="' + en_url + '" alt="English diagram"></p>'
        png = b'\x89PNG\r\n\x1a\nimage-data'
        response = {'encoding': 'base64', 'content': sync.base64.b64encode(png).decode()}
        with tempfile.TemporaryDirectory() as output, patch.object(sync, 'get_json', return_value=response) as api:
            directory = Path(output) / 'issue-media'
            directory.mkdir()
            stale = directory / 'unused.png'
            stale.write_bytes(b'unused')
            project = sync.build_feed([bilingual_issue(pt_html=pt, en_html=en)], 'owner/repo', output)['projects'][0]
            pt_images, en_images = project['translations']['pt']['images'], project['translations']['en']['images']
            self.assertEqual(api.call_count, 2)
            self.assertEqual(len(pt_images), 1)
            self.assertEqual(len(en_images), 1)
            self.assertNotEqual(pt_images, en_images)
            self.assertEqual(set(project['images']), set(pt_images + en_images))
            for path in pt_images + en_images:
                self.assertEqual((Path(output) / path).read_bytes(), png)
            self.assertFalse(stale.exists())
            self.assertIn('alt="English diagram"', project['translations']['en']['bodyHtml'])
            self.assertNotIn(pt_images[0], project['translations']['en']['bodyHtml'])
            self.assertNotIn('https://github.com', project['translations']['en']['bodyHtml'])

    def test_missing_markdown_language_markers_or_title_fail_with_issue_number(self):
        source = bilingual_issue(17)
        invalid_sources = [
            source['body'].split('<!-- portfolio:en -->')[0],
            source['body'].replace('<!-- portfolio:pt -->', ''),
            source['body'].replace('<!-- /portfolio -->', ''),
            source['body'].replace('<!-- portfolio:en -->', '<!-- portfolio:fr -->'),
            source['body'].replace('<!-- /portfolio -->', '<!-- portfolio:en -->\n<!-- /portfolio -->'),
            source['body'].replace('# My project', 'My project'),
            source['body'].replace('<summary>English</summary>', '<summary>Français</summary>'),
        ]
        with tempfile.TemporaryDirectory() as output:
            for raw in invalid_sources:
                with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, r'Issue #17:'):
                    sync.build_feed([{**source, 'body': raw}], 'owner/repo', output)

    def test_missing_or_duplicate_rendered_language_fails_instead_of_using_portuguese(self):
        source = bilingual_issue(18)
        pt = '<details><summary>Português</summary><h1>Meu projeto</h1><p>Conteúdo.</p></details>'
        with tempfile.TemporaryDirectory() as output:
            with self.assertRaisesRegex(ValueError, 'Issue #18: Missing rendered portfolio language: en'):
                sync.build_feed([{**source, 'body_html': pt}], 'owner/repo', output)
            with self.assertRaisesRegex(ValueError, 'Duplicate rendered portfolio language: pt'):
                sync.build_feed([{**source, 'body_html': pt + source['body_html']}], 'owner/repo', output)
            en = '<details><summary>English</summary><h1>My project</h1><p>Content.</p></details>'
            with self.assertRaisesRegex(ValueError, 'Issue #18: Missing rendered portfolio language: pt'):
                sync.build_feed([{**source, 'body_html': en}], 'owner/repo', output)

    def test_offline_bilingual_fixture_renders_markdown_blocks_without_wrappers(self):
        source = {**bilingual_issue(), 'body_html': None}
        with tempfile.TemporaryDirectory() as output:
            translations = sync.build_feed([source], 'owner/repo', output, offline=True)['projects'][0]['translations']
            for language in ('pt', 'en'):
                self.assertNotIn('<details', translations[language]['bodyHtml'])
                self.assertNotIn('portfolio:', translations[language]['bodyHtml'])
                self.assertNotIn(translations[language]['title'], translations[language]['bodyHtml'])
            self.assertIn('<h3>Overview</h3>', translations['en']['bodyHtml'])
            self.assertEqual(translations['en']['summary'], 'I built the application with React.')

    def test_legacy_issue_keeps_portuguese_and_gets_an_english_only_fallback(self):
        with tempfile.TemporaryDirectory() as output:
            project = sync.build_feed([issue(23, body_html='<h1>Contexto original</h1><p>Descrição do projeto.</p>')], 'owner/repo', output)['projects'][0]
            self.assertEqual(project['title'], 'Projeto 23')
            self.assertEqual(project['summary'], 'Descrição do projeto.')
            self.assertIn('<h3>Contexto original</h3>', project['bodyHtml'])
            self.assertEqual(project['translations']['pt']['bodyHtml'], project['bodyHtml'])
            en = project['translations']['en']
            self.assertEqual(en['title'], 'Project #23')
            self.assertIn('English translation', en['summary'])
            self.assertIn('https://github.com/owner/repo/issues/23', en['bodyHtml'])
            self.assertNotIn('Descrição', en['bodyHtml'])
            self.assertNotIn('Projeto', en['title'])
            self.assertEqual(en['images'], [])


if __name__ == '__main__':
    unittest.main()
