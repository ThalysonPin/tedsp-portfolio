#!/usr/bin/env python3
"""Regenerate both one-page CVs and version their download links.

Requires ReportLab. Professional experience, skills, education, languages and
contact details come from the site; selected-project summaries live below.
"""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BLUE = colors.HexColor("#123A70")
INK = colors.HexColor("#172334")
GRAY = colors.HexColor("#526071")
PROJECTS = {
    "pt": [
        ('EverBetter', 'https://betterever.tedsptech.com/',
         'Desenvolvi e mantenho uma aplicação de análise de sites para SEO e buscas com IA, com diagnóstico técnico e recomendações.'),
        ('Landpages', 'https://landpages.tedsptech.com/',
         'Criei uma vitrine de landing pages responsivas, com quatro demonstrações interativas e contato pelo WhatsApp.'),
        ('Atendimento com IA no n8n', 'https://github.com/ThalysonPin/tedsp-portfolio/issues/1',
         'Construí um sistema de 10 módulos com agentes, RAG, MCP e integrações com WhatsApp, CRMs e agendas.'),
    ],
    "en": [
        ('EverBetter', 'https://betterever.tedsptech.com/',
         'I built and maintain a website analysis app for SEO and AI search, with technical checks and recommendations.'),
        ('Landpages', 'https://landpages.tedsptech.com/',
         'I created a responsive landing page showcase with four interactive demos and WhatsApp contact links.'),
        ('AI customer service in n8n', 'https://github.com/ThalysonPin/tedsp-portfolio/issues/1',
         'I built a 10-module system with AI agents, RAG, MCP, and integrations for WhatsApp, CRMs, and calendars.'),
    ],
}


def site_constant(source: str, name: str):
    seed = DIST / 'content.json'
    if seed.exists():
        return json.loads(seed.read_text(encoding='utf-8'))[name]
    start = re.search(rf"\bconst {name}\s*=\s*", source)
    if not start:
        raise ValueError(f"Site data not found: {name}")
    return json.JSONDecoder().raw_decode(source[start.end():])[0]


def clean(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value)).replace("—", "-").replace("–", "-")


def selected(value, lang: str) -> str:
    return clean(value[lang] if isinstance(value, dict) else value)


def register_fonts():
    mac = Path('/System/Library/Fonts/Supplemental')
    fonts = [('CV', 'Arial.ttf', 'Vera.ttf'), ('CV-Bold', 'Arial Bold.ttf', 'VeraBd.ttf')]
    for name, preferred, bundled in fonts:
        path = mac / preferred
        if not path.exists():
            import reportlab
            path = Path(reportlab.__file__).parent / 'fonts' / bundled
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily('CV', normal='CV', bold='CV-Bold', italic='CV', boldItalic='CV-Bold')


def generate(lang: str, source: str, index: str) -> Path:
    text = site_constant(source, 'text')[lang]
    jobs = site_constant(source, 'jobs')
    skills = site_constant(source, 'skills')
    profile = json.loads((DIST / 'content.json').read_text(encoding='utf-8'))['profile']
    email = profile['email']
    phone = re.search(r'https://wa\.me/(\d+)', profile['whatsapp']).group(1)
    phone_label = f'+{phone[:2]} ({phone[2:4]}) {phone[4:9]}-{phone[9:]}' if len(phone) == 13 and phone.startswith('55') else '+' + phone
    pt = lang == 'pt'
    labels = ['PERFIL', 'COMPETÊNCIAS', 'EXPERIÊNCIA PROFISSIONAL', 'PROJETOS SELECIONADOS', 'FORMAÇÃO E IDIOMAS'] if pt else ['PROFILE', 'TECHNICAL SKILLS', 'PROFESSIONAL EXPERIENCE', 'SELECTED PROJECTS', 'EDUCATION & LANGUAGES']
    body = ParagraphStyle('Body', fontName='CV', fontSize=9.8, leading=11.6, textColor=INK)
    title = ParagraphStyle('Title', parent=body, fontName='CV-Bold', fontSize=24, leading=28, textColor=BLUE)
    role = ParagraphStyle('Role', parent=body, fontSize=11.5, leading=16, textColor=BLUE)
    contact = ParagraphStyle('Contact', parent=body, fontSize=8.8, leading=12, textColor=GRAY)
    heading = ParagraphStyle('Section', parent=body, fontName='CV-Bold', fontSize=10, leading=13, textColor=BLUE, spaceBefore=9, spaceAfter=5)
    job_heading = ParagraphStyle('Job', parent=body, fontName='CV-Bold', fontSize=9.9, leading=12.5)
    date = ParagraphStyle('Date', parent=contact, fontSize=8.4, leading=11, spaceAfter=2)
    job_stack = ParagraphStyle('JobStack', parent=contact, leading=11, spaceBefore=2)
    esc = html.escape
    link = lambda url, label: f'<link href="{esc(url, quote=True)}" color="#123A70">{esc(label)}</link>'
    story = [Paragraph(esc(profile['name']), title), Paragraph(esc(text['heroRole']), role)]
    location = text['location'].replace('·', '-')
    story += [
        Paragraph(f'{esc(location)} | {link("https://wa.me/" + phone, phone_label)} | {link("mailto:" + email, email)}', contact),
        Paragraph(' | '.join([link('https://tedsptech.com/', 'tedsptech.com'), link(profile['linkedin'], profile['linkedin'].removeprefix('https://www.').removeprefix('https://').rstrip('/')), link(profile['github'], profile['github'].removeprefix('https://').rstrip('/'))]), contact),
        Paragraph(labels[0], heading), Paragraph(esc(text['heroIntro']), body),
        Paragraph(labels[1], heading),
    ]
    # Keep the same stack as the site while prioritizing the main tools on one page.
    names = {item for group in skills for item in group['items']}
    preferred = ['n8n', 'Python', 'JavaScript', 'Node.js', 'React', 'Next.js', 'PostgreSQL', 'MySQL', 'Redis', 'Supabase', 'Docker', 'Portainer', 'DevOps', 'Figma', 'Git', 'OpenAI', 'RAG', 'Kommo', 'HubSpot', 'GoHighLevel', 'WhatsApp']
    stack = ', '.join(item for item in preferred if item in names)
    stack += '. APIs REST, webhooks, LLMs e integrações com CRMs e Google Calendar.' if pt else '. REST APIs, webhooks, LLMs, and integrations with CRMs and Google Calendar.'
    story += [Paragraph(esc(stack), body), Paragraph(labels[2], heading)]
    technologies = ('Docker', 'Portainer', 'Redis', 'PostgreSQL', 'MySQL', 'Figma')
    infrastructure = ('AWS', 'Hetzner', 'Hostinger', 'Contabo', 'Ubuntu', 'Debian')
    for job in jobs:
        company = selected(job['company'], lang)
        desc = selected(job['description'], lang)
        if company == 'B2Med':
            desc += ' ' + selected(job['extra'], lang)
        block = [
            Paragraph(esc(company) + ' | ' + esc(selected(job['title'], lang)), job_heading),
            Paragraph(esc(selected(job['date'], lang)), date),
            Paragraph(esc(desc), body),
        ]
        tags = job['tags']
        highlights = [tool for tool in technologies if tool in tags]
        if 'DevOps' in tags:
            platforms = ', '.join(platform for platform in infrastructure if platform in tags)
            highlights.append(f'DevOps ({platforms})' if platforms else 'DevOps')
        if highlights:
            block.append(Paragraph(esc(' · '.join(highlights)), job_stack))
        block.append(Spacer(1, 5))
        story.append(KeepTogether(block))
    story.append(Paragraph(labels[3], heading))
    for name, url, description in PROJECTS[lang]:
        story.append(Paragraph(f'<b>{link(url, name)}</b> - {esc(description)}', body))
        story.append(Spacer(1, 3))
    story.append(Paragraph(labels[4], heading))
    school = clean(text['educationSchool']).replace('·', '-')
    progress = 'em andamento' if pt else 'in progress'
    story.append(Paragraph(esc(text['educationTitle'] + ' - ' + school + ', ' + progress + '.'), body))
    languages = clean(text['languageDescription'].replace('<br>', '. ')) + '.'
    story.append(Paragraph(esc(languages), body))
    output = DIST / f'curriculo-thalyson-{lang}.pdf'
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=34, leftMargin=34, topMargin=30, bottomMargin=32,
                            title=f'CV - {profile["name"]} - {text["heroRole"]}', author=profile['name'],
                            subject='Currículo profissional' if pt else 'Professional CV', pageCompression=1)

    def footer(canvas, document):
        if document.page > 1:
            raise ValueError(f'CV {lang} exceeds one page; shorten the copy before publishing.')
        canvas.setStrokeColor(colors.HexColor('#D4DCE7'))
        canvas.line(34, 25, A4[0] - 34, 25)
        canvas.setFont('CV', 7)
        canvas.setFillColor(GRAY)
        canvas.drawString(34, 14, profile['name'] + ' | ' + profile['brand'])
        canvas.drawRightString(A4[0] - 34, 14, 'tedsptech.com')

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output


def main():
    register_fonts()
    app_path = DIST / 'app.js'
    index_path = DIST / 'index.html'
    app, index = app_path.read_text(encoding='utf-8'), index_path.read_text(encoding='utf-8')
    outputs = [generate(lang, app, index) for lang in ('pt', 'en')]
    version = hashlib.sha256(b''.join(path.read_bytes() for path in outputs)).hexdigest()[:12]
    declaration = f"const resumeVersion='{version}';"
    if re.search(r'const resumeVersion=.*?;', app):
        app = re.sub(r'const resumeVersion=.*?;', declaration, app)
    else:
        app = app.replace("let language='pt';", declaration + "\nlet language='pt';")
    app = re.sub(r'`curriculo-thalyson-\$\{lang\}\.pdf(?:\?v=\$\{resumeVersion\})?`', '`curriculo-thalyson-${lang}.pdf?v=${resumeVersion}`', app)
    index = re.sub(r'curriculo-thalyson-pt\.pdf(?:\?v=[^"\s]+)?', f'curriculo-thalyson-pt.pdf?v={version}', index)
    index = re.sub(r'app\.js\?v=[^"\s]+', f'app.js?v=cv-{version}', index)
    app_path.write_text(app, encoding='utf-8')
    index_path.write_text(index, encoding='utf-8')
    seed_path = DIST / 'content.json'
    if seed_path.exists():
        seed = json.loads(seed_path.read_text(encoding='utf-8'))
        seed['profile']['resume'] = {lang: f'curriculo-thalyson-{lang}.pdf?v={version}' for lang in ('pt', 'en')}
        seed_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        payload = json.dumps(seed, ensure_ascii=False).replace('<', '\\u003c')
        (DIST / 'site-content.js').write_text('window.PORTFOLIO_CONTENT = ' + payload + ';\n', encoding='utf-8')
    for path in outputs:
        print(f'{path.relative_to(ROOT)} ({path.stat().st_size} bytes)')
    print(f'Download version: {version}')


if __name__ == '__main__':
    main()
