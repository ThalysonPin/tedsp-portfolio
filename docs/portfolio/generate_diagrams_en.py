"""English diagrams for the bilingual portfolio. Requires Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

OUT = Path(__file__).parent / 'images'
OUT.mkdir(exist_ok=True)
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
BG, INK, MUTED, BLUE, LINE, PALE = '#f5f8ff', '#132746', '#526580', '#2056ce', '#c9d8ed', '#e8f0ff'

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def canvas(tag, title, subtitle, height=1240):
    im = Image.new('RGB', (1800, height), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((64,48,64+int(d.textlength(tag,font=font(22,True)))+42,96),radius=10,fill=BLUE)
    d.text((85,59),tag,font=font(22,True),fill='white')
    d.text((64,130),title,font=font(47,True),fill=INK)
    d.text((64,202),subtitle,font=font(26),fill=MUTED)
    return im,d

def box(d,rect,label,title,lines=(),pale=False):
    x,y,x2,y2=rect
    d.rounded_rectangle(rect,radius=18,fill=PALE if pale else 'white',outline=LINE,width=2)
    for offset,text,size,bold,color in [(22,label,21,True,BLUE),(62,title,30,True,INK)]+[(112+35*n,line,24,False,MUTED) for n,line in enumerate(lines)]:
        while d.textlength(text,font=font(size,bold))>x2-x-48:
            size-=1
        if size<18 or y+offset+size>y2-12:
            raise ValueError('Text does not fit: '+text)
        d.text((x+24,y+offset),text,font=font(size,bold),fill=color)

def arrow(d,points,muted=False):
    color=MUTED if muted else BLUE
    d.line(points,fill=color,width=4,joint='curve')
    a,b=points[-2:];angle=math.atan2(b[1]-a[1],b[0]-a[0])
    d.polygon([b,(b[0]-17*math.cos(angle-.5),b[1]-17*math.sin(angle-.5)),(b[0]-17*math.cos(angle+.5),b[1]-17*math.sin(angle+.5))],fill=color)

def footer(d,first,height=1240):
    d.line((64,height-140,1736,height-140),fill=LINE,width=2)
    d.text((64,height-110),first,font=font(24,True),fill=INK)
    d.text((64,height-60),'Architecture diagram based on my project notes. This is not an application screenshot.',font=font(23),fill=MUTED)

im,d=canvas('HR / FULL-STACK','Recruitment management with Kanban','React · Material UI · Go · PostgreSQL | Proprietary project, 2022–2023')
box(d,(64,300,510,515),'INTERFACE','React + Material UI',['Kanban board and filters','Used by the HR team'])
box(d,(660,300,1106,515),'SERVICES','Go API',['Processes, stages and profiles','Reports and resumes'])
box(d,(1260,300,1736,515),'DATA','PostgreSQL',['Candidates, processes and stages','Queries for reports'])
arrow(d,[(510,408),(660,408)]);arrow(d,[(1106,408),(1260,408)])
d.text((526,360),'HTTP / JSON',font=font(18,True),fill=BLUE)
box(d,(1260,630,1736,825),'DOCUMENTS','PDF resumes',['Files linked to each candidate'])
arrow(d,[(883,515),(883,727),(1260,727)])
box(d,(64,630,700,825),'FOLLOW-UP','Shared hiring pipeline',['Contact history by stage','Team visibility into each process'],True)
box(d,(64,900,1736,1060),'MY ROLE','Solo full-stack development',['Product and UX · Frontend · Backend · Database'],True)
footer(d,'PDF storage provider and hosting details are not included in these project notes.')
im.save(OUT/'2-architecture.en.png',optimize=True)

im,d=canvas('PIX / REGISTRATION','Checkout for a beach tennis tournament','React · Tailwind CSS · Material UI · Node.js · PostgreSQL | 2024')
box(d,(64,300,525,515),'01 / DISCOVERY','Landing page',['Tournament information','Registration call to action'])
box(d,(670,300,1131,515),'02 / REGISTRATION','Checkout without login',['Athletes, partners and categories','CPF and tournament rules'])
box(d,(1276,300,1736,515),'03 / PAYMENT','Custom Pix BR Code',['QR code and copy-and-paste code','Payment amount included'])
arrow(d,[(525,407),(670,407)]);arrow(d,[(1131,407),(1276,407)])
box(d,(64,650,525,865),'INTERFACE','React',['Tailwind CSS and Material UI','UX research and event branding'],True)
box(d,(670,650,1131,865),'SERVICES AND DATA','Node.js + PostgreSQL',['Registration rules and records','Pix payload generation'],True)
box(d,(1276,650,1736,865),'04 / CONFIRMATION','WhatsApp support',['Manual reconciliation','No automatic payment confirmation'])
arrow(d,[(1506,515),(1506,650)])
d.text((64,953),'100+ REGISTRATIONS SOLD',font=font(34,True),fill=BLUE)
d.text((64,1005),'No third-party payment gateway or checkout in this flow.',font=font(27),fill=MUTED)
footer(d,'Planned next step: PSP Pix API and webhooks to automate payment confirmation.')
im.save(OUT/'3-checkout.en.png',optimize=True)

im,d=canvas('AI / ANALYTICS','Conversation analytics for medical clinics','React · Supabase · PostgreSQL + RLS · n8n · OpenRouter · Uazapi | 2026')
box(d,(64,300,495,515),'MESSAGES','WhatsApp + Uazapi',['Front-desk / patient conversations','Passive monitoring'])
box(d,(650,300,1081,515),'ORCHESTRATION','n8n workflows',['Ingestion, analysis and reports','Structured records'])
box(d,(1236,300,1736,515),'INTELLIGENCE','LLMs via OpenRouter',['Structured conversation analysis','Objections, sentiment and status'])
arrow(d,[(495,408),(650,408)]);arrow(d,[(1081,390),(1236,390)]);arrow(d,[(1236,445),(1081,445)])
box(d,(650,650,1081,865),'PERSISTENCE','Supabase / PostgreSQL',['RLS per clinic','Records for the dashboard'],True)
box(d,(1236,650,1736,865),'DASHBOARD','React',['Metrics and automatic Kanban','Contact context and reports'],True)
arrow(d,[(866,515),(866,650)]);arrow(d,[(1081,757),(1236,757)])
box(d,(64,650,495,865),'WEEKLY DELIVERY','WhatsApp report',['Summary sent to the clinic','Through n8n and Uazapi'])
arrow(d,[(650,480),(575,480),(575,596),(280,596),(280,650)])
d.text((64,953),'30+ CLINICS · 100,000+ CONVERSATIONS ANALYZED',font=font(34,True),fill=BLUE)
d.text((64,1005),'This diagram contains no real patient conversations.',font=font(27),fill=MUTED)
footer(d,'A daily report is also generated; its delivery channel is not specified here.')
im.save(OUT/'4-analytics.en.png',optimize=True)

im,d=canvas('n8n / AI','Modular customer service system','10 modules: 1 entry workflow + 9 subworkflows',1570)
box(d,(64,290,540,500),'MODULE 1','Entry channel',['Client settings, hours and rules','Routing and human handoff rules'])
box(d,(662,290,1138,500),'MODULE 2','Kommo and session ID',['Contact eligibility','Session lookup and history'])
box(d,(1260,290,1736,500),'MODULE 3','Classification and queue',['Text, audio, images and PDFs','Message batching with Redis'])
arrow(d,[(540,395),(662,395)]);arrow(d,[(1138,395),(1260,395)])
d.text((1020,540),'Alternative agents selected per client',font=font(25,True),fill=BLUE)
box(d,(1000,605,1350,825),'MODULE 4','BASIC agent',['Memory and RAG','Kommo MCP'])
box(d,(1400,605,1736,825),'MODULE 4.1','Dual MCP agent',['Memory and RAG','Kommo + second MCP'])
arrow(d,[(1498,500),(1498,575),(1175,575),(1175,605)]);arrow(d,[(1498,575),(1568,575),(1568,605)])
box(d,(1100,960,1736,1180),'MODULE 5','Agent response delivery',['Handoff checks, formatting, text or audio','Delivery, history and follow-ups'])
arrow(d,[(1175,825),(1175,890),(1300,890),(1300,960)]);arrow(d,[(1568,825),(1568,890),(1530,890),(1530,960)])
box(d,(64,605,485,825),'SUPPORT WORKFLOW','Human chat history',['Session and conversation memory','Incoming messages and audio'],True)
box(d,(535,605,945,825),'SUPPORT WORKFLOW','RAG updates',['Documents → chunks','Embeddings → Pinecone'],True)
box(d,(64,960,485,1180),'SUPPORT WORKFLOW','Reset',['Clear one contact’s records','Start a new session'],True)
box(d,(535,960,1000,1180),'SUPPORT WORKFLOW','Notify supervisor',['Conversation context and notification','Follow-up and configured CRM actions'],True)
arrow(d,[(945,715),(1000,715)],True)
d.text((64,1260),'The two agents are alternatives, not consecutive steps.',font=font(28,True),fill=BLUE)
d.text((64,1310),'Support workflows run as needed; the diagram shows a simplified view of their connections.',font=font(26),fill=MUTED)
footer(d,'I kept the original numbering: module 4.1 is a separate subworkflow.',1570)
im.save(OUT/'1-flow.en.png',optimize=True)

im,d=canvas('n8n / INTEGRATIONS','Connected services','Channels, data, CRM, AI, knowledge and tools',1410)
cards=[('CHANNELS AND DELIVERY','WhatsApp and voice',['UAZAPI · Official WhatsApp API','ElevenLabs · Discord']),('DATA AND CONTEXT','Persistence and queues',['Supabase · PostgreSQL','Self-hosted Redis','Sessions, memory and follow-ups']),('SALES AND OPERATIONS','CRM and configuration',['Kommo CRM · ClickUp','My own internal CRM']),('ARTIFICIAL INTELLIGENCE','Agents and media',['OpenRouter · OpenAI embeddings','GPT Transcribe · GPT Image']),('KNOWLEDGE','Documents and RAG',['Google Docs · Google Drive','Pinecone vector database']),('MCP TOOLS','External systems',['Kommo MCP','My own internal MCP','Clinical systems and scheduling'])]
for i,(label,title,lines) in enumerate(cards):
    x=64+(i%3)*570;y=280+(i//3)*315
    box(d,(x,y,x+532,y+268),label,title,lines)
box(d,(64,950,1736,1210),'CLINICAL SYSTEMS AND SCHEDULING','Systems connected through my internal MCP',['GestãoDS · Feegow · Clínica nas Nuvens · Amigo','Ninsaúde · Quarkclinic · Google Calendar','Tools are enabled according to each client’s configuration.'],True)
footer(d,'This is the integration inventory; a client does not necessarily use every service.',1410)
im.save(OUT/'1-integrations.en.png',optimize=True)
print('Generated five English diagrams in',OUT)
