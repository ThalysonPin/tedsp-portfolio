"""Renderiza diagramas esquemáticos dos estudos de caso do portfólio."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

ROOT = Path(__file__).resolve().parents[1]
REGULAR = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
BG, WHITE, INK, MUTED, BLUE, LINE, PALE = '#f5f8ff', '#ffffff', '#132746', '#526580', '#2056ce', '#c9d8ed', '#e8f0ff'

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else REGULAR, size)

def canvas(tag, title, subtitle):
    im = Image.new('RGB', (1800, 1240), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((64, 48, 64 + int(d.textlength(tag, font=font(22, True))) + 42, 96), radius=10, fill=BLUE)
    d.text((85, 59), tag, font=font(22, True), fill=WHITE)
    d.text((64, 130), title, font=font(49, True), fill=INK)
    d.text((64, 202), subtitle, font=font(27), fill=MUTED)
    return im, d

def box(d, rect, label, title, lines=(), pale=False):
    x, y, x2, y2 = rect
    d.rounded_rectangle(rect, radius=18, fill=PALE if pale else WHITE, outline=LINE, width=2)
    label_font = font(21, True)
    d.text((x+24, y+22), label, font=label_font, fill=BLUE)
    title_size = 31
    while d.textlength(title, font=font(title_size, True)) > x2-x-48:
        title_size -= 1
    d.text((x+24, y+62), title, font=font(title_size, True), fill=INK)
    for n, line in enumerate(lines):
        if d.textlength(line, font=font(24)) > x2-x-48:
            raise ValueError('Linha excede o bloco: ' + line)
        d.text((x+24, y+112+n*35), line, font=font(24), fill=MUTED)

def arrow(d, points, muted=False):
    color = MUTED if muted else BLUE
    d.line(points, fill=color, width=4, joint='curve')
    a,b=points[-2:]
    angle=math.atan2(b[1]-a[1], b[0]-a[0])
    d.polygon([b,(b[0]-17*math.cos(angle-.5),b[1]-17*math.sin(angle-.5)),(b[0]-17*math.cos(angle+.5),b[1]-17*math.sin(angle+.5))], fill=color)

def footer(d, first, second='Diagrama esquemático baseado no relato do autor. Não é captura da aplicação.'):
    d.line((64, 1100, 1736, 1100), fill=LINE, width=2)
    d.text((64, 1130), first, font=font(25, True), fill=INK)
    d.text((64, 1180), second, font=font(23), fill=MUTED)

def save(im, slug):
    path=ROOT/slug/'imagens'/'01-arquitetura.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)
    print(path.relative_to(ROOT.parent))

im,d=canvas('RH / FULL-STACK', 'Gestão de recrutamento com Kanban', 'React · Material UI · Go · PostgreSQL | Projeto proprietário, 2022–2023')
box(d,(64,300,510,515),'INTERFACE','React + Material UI',['Kanban e filtros','Uso pela equipe de RH'])
box(d,(660,300,1106,515),'SERVIÇOS','API em Go',['Processos, etapas e perfis','Relatórios e currículos'])
box(d,(1260,300,1736,515),'DADOS','PostgreSQL',['Candidatos, processos e etapas','Consultas para relatórios'])
arrow(d,[(510,408),(660,408)])
d.text((528,360),'HTTP / JSON',font=font(18,True),fill=BLUE)
arrow(d,[(1106,408),(1260,408)])
box(d,(1260,630,1736,825),'DOCUMENTOS','Currículos em PDF',['Arquivos ligados ao candidato'])
arrow(d,[(883,515),(883,727),(1260,727)])
box(d,(64,630,700,825),'ACOMPANHAMENTO','Funil compartilhado',['Contato e histórico por etapa','Visão do andamento para a equipe'],pale=True)
box(d,(64,900,1736,1060),'MINHA ATUAÇÃO','Desenvolvimento full-stack solo',['Produto e UX · Frontend · Backend · Banco de dados'],pale=True)
footer(d,'PDF: o relatório não especifica o serviço de armazenamento ou a hospedagem.')
save(im,'hr-recruitment-system')

im,d=canvas('PIX / INSCRIÇÕES', 'Checkout para torneio de beach tennis', 'React · Tailwind CSS · Material UI · Node.js · PostgreSQL | 2024')
box(d,(64,300,525,515),'01 / DESCOBERTA','Landing page',['Informações do torneio','CTA para inscrição'])
box(d,(670,300,1131,515),'02 / INSCRIÇÃO','Checkout sem login',['Atletas, parceiros e categorias','CPF e regras do regulamento'])
box(d,(1276,300,1736,515),'03 / PAGAMENTO','Pix autoral (BR Code)',['QR code e código copia e cola','Valor definido na cobrança'])
arrow(d,[(525,407),(670,407)]);arrow(d,[(1131,407),(1276,407)])
box(d,(64,650,525,865),'INTERFACE','React',['Tailwind CSS e Material UI','Pesquisa de UX e branding'],pale=True)
box(d,(670,650,1131,865),'SERVIÇOS E DADOS','Node.js + PostgreSQL',['Regras e dados das inscrições','Geração do payload Pix'],pale=True)
box(d,(1276,650,1736,865),'04 / CONFIRMAÇÃO','Suporte no WhatsApp',['Conciliação manual','Sem confirmação por webhook'])
arrow(d,[(1506,515),(1506,650)])
d.text((64,953),'MAIS DE 100 INSCRIÇÕES VENDIDAS',font=font(34,True),fill=BLUE)
d.text((64,1005),'Sem gateway ou checkout de terceiros no fluxo descrito.',font=font(27),fill=MUTED)
footer(d,'Evolução proposta: API Pix de PSP com cobranças e webhooks para conciliação automática.')
save(im,'pix-checkout-beach-tennis')

im,d=canvas('IA / ANALYTICS', 'Inteligência de conversas para clínicas', 'React · Supabase · PostgreSQL + RLS · n8n · OpenRouter · Uazapi | 2026')
box(d,(64,300,495,515),'MENSAGENS','WhatsApp + Uazapi',['Conversa recepção / paciente','Monitoramento passivo'])
box(d,(650,300,1081,515),'ORQUESTRAÇÃO','Workflows n8n',['Ingestão, análise e relatórios','Organização dos dados'])
box(d,(1236,300,1736,515),'INTELIGÊNCIA','LLMs via OpenRouter',['Análise estruturada do contexto','Objeções, sentimento e status'])
arrow(d,[(495,408),(650,408)]);arrow(d,[(1081,390),(1236,390)])
arrow(d,[(1236,445),(1081,445)])
box(d,(650,650,1081,865),'PERSISTÊNCIA','Supabase / PostgreSQL',['RLS por clínica','Dados para consulta'],pale=True)
box(d,(1236,650,1736,865),'CONSULTA','Dashboard React',['Indicadores e Kanban automático','Contexto e relatórios por contato'],pale=True)
arrow(d,[(866,515),(866,650)]);arrow(d,[(1081,757),(1236,757)])
box(d,(64,650,495,865),'ENTREGA SEMANAL','Relatório no WhatsApp',['Resumo enviado para a clínica','Via workflows e Uazapi'])
arrow(d,[(650,480),(575,480),(575,596),(280,596),(280,650)])
d.text((64,953),'30+ CLÍNICAS · 100.000+ CONVERSAS ANALISADAS',font=font(34,True),fill=BLUE)
d.text((64,1005),'Resultados informados pelo autor. Nenhuma conversa real é exibida neste diagrama.',font=font(26),fill=MUTED)
footer(d,'O canal de entrega do relatório diário não foi especificado no material de origem.')
save(im,'whatsapp-clinic-analytics')
