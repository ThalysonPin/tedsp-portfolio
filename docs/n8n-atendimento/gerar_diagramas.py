from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

OUT = Path(__file__).parent / 'imagens'
OUT.mkdir(parents=True, exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
BG, INK, MUTED, GREEN, LINE = '#f6f8f7', '#172b24', '#53665e', '#17634b', '#cbd9d2'
def font(size, bold=False): return ImageFont.truetype(BOLD if bold else FONT, size)
def canvas(title, subtitle, height):
    im = Image.new('RGB', (1800, height), BG); d = ImageDraw.Draw(im)
    d.rounded_rectangle((64, 55, 190, 100), radius=12, fill=GREEN)
    d.text((88, 63), 'n8n / IA', font=font(22, True), fill='white')
    d.text((64, 127), title, font=font(49, True), fill=INK)
    d.text((64, 194), subtitle, font=font(26), fill=MUTED)
    return im, d
def block(d, rect, number, title, lines, fill='white', accent=GREEN):
    x,y,x2,y2=rect
    d.rounded_rectangle(rect, radius=22, fill=fill, outline=LINE, width=2)
    label_size=22
    while d.textlength(number, font=font(label_size, True)) > x2-x-44: label_size-=1
    d.text((x+22,y+20), number, font=font(label_size,True), fill=accent)
    d.text((x+22,y+57), title, font=font(29,True), fill=INK)
    for i,line in enumerate(lines): d.text((x+22,y+101+i*34), line, font=font(23), fill=MUTED)
def arrow(d, points, color=GREEN, dashed=False):
    for a,b in zip(points, points[1:]):
        if dashed:
            n=max(1,int(math.dist(a,b)/14))
            for i in range(0,n,2):
                p=lambda t:(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
                d.line((p(i/n),p(min(i+1,n)/n)),fill=color,width=4)
        else: d.line((a,b),fill=color,width=4)
    a,b=points[-2:]; ang=math.atan2(b[1]-a[1],b[0]-a[0])
    d.polygon([b,(b[0]-17*math.cos(ang-.5),b[1]-17*math.sin(ang-.5)),(b[0]-17*math.cos(ang+.5),b[1]-17*math.sin(ang+.5))],fill=color)

im,d=canvas('Arquitetura modular de atendimento', '10 módulos = 1 canal de entrada + 9 subworkflows', 1570)
block(d,(64,275,540,480),'MÓDULO 1','Canal de entrada',['Cliente, regras e bloqueios','UAZAPI / WhatsApp oficial'])
block(d,(662,275,1138,480),'MÓDULO 2','Kommo e session ID',['Elegibilidade do contato','CRM, sessão e histórico'])
block(d,(1260,275,1736,480),'MÓDULO 3','Classificação e fila',['Texto, áudio, imagem, PDF','Agrupamento via Redis'])
arrow(d,[(540,378),(662,378)]);arrow(d,[(1138,378),(1260,378)])
d.text((1040,521),'Seleção conforme o cliente',font=font(23,True),fill=GREEN)
block(d,(1030,590,1390,808),'MÓDULO 4','Agente BASIC',['Memória + RAG','MCP do Kommo'])
block(d,(1450,590,1736,808),'MÓDULO 4.1','Duplo MCP',['Memória + RAG','Kommo + 2º MCP'])
arrow(d,[(1498,480),(1498,555),(1210,555),(1210,590)])
arrow(d,[(1498,555),(1593,555),(1593,590)])
block(d,(1150,930,1736,1148),'MÓDULO 5','Envio da resposta',['Bloqueios, formatação, texto ou áudio','Envio, histórico e follow-up'])
arrow(d,[(1210,808),(1210,867),(1370,867),(1370,930)])
arrow(d,[(1593,808),(1593,867),(1510,867),(1510,930)])
arrow(d,[(1443,1148),(1443,1205)])
d.rounded_rectangle((1220,1205,1666,1280),radius=16,fill=GREEN)
d.text((1295,1224),'Resposta no WhatsApp',font=font(27,True),fill='white')
block(d,(64,590,494,808),'APOIO / SOB DEMANDA','Grava histórico humano',['Sessão e memória conversacional','Registro de mensagens e áudios'],fill='#ecf3ef')
block(d,(64,860,494,1078),'APOIO / SOB DEMANDA','Reset',['Limpeza por contato / telefone','Reinicialização da sessão'],fill='#ecf3ef')
arrow(d,[(220,480),(220,540),(279,540),(279,590)],color=MUTED,dashed=True)
arrow(d,[(95,480),(35,480),(35,969),(64,969)],color=MUTED,dashed=True)
block(d,(555,590,950,808),'APOIO / BASE DE CONHECIMENTO','Atualiza RAG',['Documentos → trechos','Embeddings → Pinecone'],fill='#ecf3ef')
arrow(d,[(950,699),(1030,699)],color=MUTED,dashed=True)
block(d,(555,930,1000,1148),'APOIO / INTERVENÇÃO','Aciona supervisor',['Contexto e aviso ao responsável','Follow-up e ações no CRM'],fill='#ecf3ef')
arrow(d,[(1030,765),(1008,765),(1008,881),(778,881),(778,930)],color=MUTED,dashed=True)
d.text((64,1335),'Linha contínua: caminho principal. Linha tracejada: apoio ou acionamento condicional.',font=font(25),fill=MUTED)
d.text((64,1380),'BASIC e Duplo MCP são alternativas de atendimento, escolhidas por configuração.',font=font(25),fill=MUTED)
d.text((64,1420),'Ambos consultam a base RAG e podem acionar o supervisor; conexões de apoio resumidas.',font=font(25),fill=MUTED)
d.text((64,1490),'Diagrama esquemático baseado na descrição do autor; não é captura do editor do n8n.',font=font(23),fill=MUTED)
im.save(OUT/'01-arquitetura-modular.png', optimize=True)

im,d=canvas('Integrações do ecossistema', 'Serviços conectados à automação modular no n8n', 1410)
cards=[
 ('CANAIS E ENTREGA','WhatsApp e voz',['UAZAPI','API oficial do WhatsApp','ElevenLabs · Discord']),
 ('DADOS E CONTEXTO','Persistência e fila',['Supabase · PostgreSQL','Redis self-hosted','Sessões, memória e follow-ups']),
 ('ATENDIMENTO E OPERAÇÃO','CRM e configuração',['Kommo CRM','ClickUp','CRM interno de autoria própria']),
 ('INTELIGÊNCIA ARTIFICIAL','Agentes e mídia',['OpenRouter · OpenAI embeddings','GPT Transcribe · GPT Image','Áudio, imagem e ferramentas']),
 ('CONHECIMENTO','Documentos e RAG',['Google Docs · Google Drive','Pinecone (banco vetorial)','Documentos, trechos e pesquisa']),
 ('FERRAMENTAS VIA MCP','Sistemas conectados',['MCP do Kommo','MCP criado internamente','Sistemas clínicos e agenda']),
 ]
for i,(label,title,lines) in enumerate(cards):
    x=64+(i%3)*570; y=280+(i//3)*315
    block(d,(x,y,x+532,y+268),label,title,lines)
d.rounded_rectangle((64,950,1736,1265),radius=22,fill='#ecf3ef',outline=LINE,width=2)
d.text((90,978),'SISTEMAS CLÍNICOS E AGENDAMENTO VIA MCP INTERNO',font=font(25,True),fill=GREEN)
d.text((90,1034),'GestãoDS  ·  Feegow  ·  Clínica nas Nuvens  ·  Amigo',font=font(32,True),fill=INK)
d.text((90,1096),'Ninsaúde  ·  Quarkclinic  ·  Google Calendar',font=font(32,True),fill=INK)
d.text((90,1162),'Ferramentas disponíveis conforme a configuração de cada cliente.',font=font(27),fill=MUTED)
d.text((90,1206),'Acesso a sistemas, prontuários e recursos de agendamento.',font=font(27),fill=MUTED)
d.text((64,1324),'Mapa de integrações informado pelo autor; não implica uso simultâneo em todos os clientes.',font=font(23),fill=MUTED)
im.save(OUT/'02-mapa-integracoes.png', optimize=True)
