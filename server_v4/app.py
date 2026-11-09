#!/usr/bin/env python3
"""Content Factory Control Plane 4.0 -- Python stdlib, SQLite, approval-first.

No remote code execution. No paid API calls unless separately configured.
Interface binds only to loopback; use an authenticated tunnel for access.
"""
import html
import io
import zipfile
import json
import os
import re
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from carousel import slide_svg

HERE = Path(__file__).resolve().parent
DATA = Path(os.getenv('CF_DATA_DIR', '/var/lib/contentfactory-v4'))
DB = DATA / 'factory.sqlite3'
ROLES_FILE = HERE / 'agents' / 'roles.json'
HOST = '127.0.0.1'  # NEVER bind public without authenticated reverse proxy
PORT = int(os.getenv('CF_PORT', '8765'))
MODEL = os.getenv('CF_WORKERS_MODEL', '@cf/meta/llama-3.1-8b-instruct')
STOP = threading.Event()

BRAND = {
    'name': 'AI без рутины',
    'niche': 'Обучение нейросетям и делегирование рутины ИИ-агентам',
    'audience': 'Начинающие, удалённые специалисты, самозанятые, предприниматели',
    'product': 'Настрой ИИ под себя',
    'price_rub': 199,
    'gross_goal_rub': 50000,
    'funnel': 'Органический пост или карусель → практическая польза → Telegram → продукт',
    'cta': 'Напиши «НАСТРОЙ» в Telegram',
    'tone': 'Просто, конкретно, без манипуляций, неподтверждённых цифр и обещаний дохода',
    'look': 'Сильный первый экран, крупная типографика, реалистичные ситуации, понятные иллюстрации',
    'approval_required': True,
    'autopost_enabled': False,
    'platforms': ['vk', 'telegram', 'instagram', 'dzen'],
    'content_types': ['carousel_8', 'post', 'article'],
}
TOPICS = [
    ('7 ошибок, из-за которых ChatGPT отвечает расплывчато', 'ошибки'),
    ('Как превратить голосовую заметку в план задач', 'практика'),
    ('Как составить промпт за 60 секунд', 'практика'),
    ('Что можно делегировать ИИ, а что нельзя', 'агенты'),
    ('5 бытовых задач, которые можно автоматизировать', 'практика'),
    ('Почему «сделай красиво» — плохая задача для ИИ', 'ошибки'),
    ('Как проверить факты в ответе нейросети', 'безопасность'),
    ('Промпт для подготовки письма клиенту', 'практика'),
    ('Как создать личный брендбук для нейросети', 'практика'),
    ('Когда ИИ-агент полезнее одного промпта', 'агенты'),
    ('Как с нуля собрать недельный контент-план', 'контент'),
    ('Три признака выдуманной ссылки от ИИ', 'безопасность'),
    ('Как найти повторяющиеся задачи в своей работе', 'практика'),
    ('Промпт для разбора сложного документа', 'практика'),
    ('Как организовать папки и файлы для ИИ', 'система'),
    ('ИИ-помощник для подготовки встреч: сценарий', 'агенты'),
    ('Почему ИИ не обязан соглашаться с вами', 'ошибки'),
    ('Как превратить 1 статью в 5 материалов', 'контент'),
    ('Промпт для сравнения вариантов без фантазий', 'практика'),
    ('Как сформулировать задачу в четыре строки', 'практика'),
    ('Идеальная проверка ответа перед публикацией', 'безопасность'),
    ('Как подготовить Telegram-пост из заметок', 'контент'),
    ('Мифы про полностью автономных ИИ-агентов', 'агенты'),
    ('Что делать, если ИИ упорно ошибается', 'ошибки'),
    ('Промпт для составления простого чек-листа', 'практика'),
    ('Как вести библиотеку удачных промптов', 'система'),
    ('Как собрать еженедельный отчёт с ИИ', 'практика'),
    ('Пять способов улучшить первый экран карусели', 'контент'),
    ('Как проверить, не раскрываете ли вы данные ИИ', 'безопасность'),
    ('Чем готовые шаблоны ИИ отличаются от личной настройки', 'продукт'),
]


def dt():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def con():
    DATA.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA busy_timeout=20000')
    return c


def init():
    roles = json.loads(ROLES_FILE.read_text('utf-8'))
    with con() as c:
        c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, title TEXT, responsibility TEXT, instructions TEXT, active INTEGER DEFAULT 1)')
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, topic TEXT NOT NULL, rubric TEXT NOT NULL,
            status TEXT NOT NULL, scheduled_at TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, payload TEXT, notes TEXT, error TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS publications (
            task_id TEXT NOT NULL, platform TEXT NOT NULL, status TEXT NOT NULL,
            remote_id TEXT, published_at TEXT, error TEXT,
            PRIMARY KEY(task_id, platform))''')
        for k, v in BRAND.items():
            c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)', (k, json.dumps(v, ensure_ascii=False)))
        for k, v in roles.items():
            c.execute('INSERT OR IGNORE INTO agents VALUES(?,?,?,?,1)',
                      (k, v['title'], v['responsibility'], v['instructions']))
        n = c.execute('SELECT count(*) FROM tasks').fetchone()[0]
        if n == 0:
            today = datetime.now(timezone.utc).date()
            for i, (topic, rubric) in enumerate(TOPICS):
                uid = uuid.uuid4().hex[:12]
                planned = datetime.combine(today + timedelta(days=i), datetime.min.time(), timezone.utc).replace(hour=12).isoformat()
                c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)',
                          (uid,topic,rubric,'waiting_for_model',planned,dt(),dt(),None,'План на месяц. Требует генерации и проверки.',None))


def settings():
    with con() as c:
        return {r['key']:json.loads(r['value']) for r in c.execute('SELECT key,value FROM settings')}


def list_agents():
    with con() as c:
        return [dict(r) for r in c.execute('SELECT id,title,responsibility,active FROM agents ORDER BY id')]


def list_tasks(limit=70):
    with con() as c:
        return [dict(r) for r in c.execute('SELECT id,topic,rubric,status,scheduled_at,updated_at,error FROM tasks ORDER BY scheduled_at LIMIT ?', (limit,))]


def task(uid):
    with con() as c:
        r = c.execute('SELECT * FROM tasks WHERE id=?',(uid,)).fetchone()
        if not r:
            raise ValueError('Задача не найдена')
        d = dict(r)
        d['payload'] = json.loads(d['payload']) if d['payload'] else None
        return d


def add_task(topic, rubric='практика'):
    topic = str(topic).strip()[:400]
    if len(topic) < 7:
        raise ValueError('Опиши тему хотя бы семью символами')
    uid = uuid.uuid4().hex[:12]
    with con() as c:
        c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (uid,topic,str(rubric)[:40],'waiting_for_model',None,dt(),dt(),None,'Добавлена вручную',None))
    return uid


def editorial_prompt(topic):
    roles = json.loads(ROLES_FILE.read_text('utf-8'))
    brand = settings()
    blocks = '\n'.join(f'[{k}]: {v["instructions"]}' for k,v in roles.items() if k in ('strategist','researcher','editor','designer','qa'))
    return (f'СОЗДАЙ КОНТЕНТ-ПАКЕТ НА РУССКОМ. Тема: {topic}\n'
            f'Брендбук: {json.dumps(brand,ensure_ascii=False)}\n'
            f'Роли и стандарты:\n{blocks}\n'
            'Выведи только валидный JSON-объект с ключами: '
            'title (строка), hook (строка), slides (список ровно из 8 объектов '
            '{headline,body,visual_prompt}), vk_post (строка), '
            'telegram_post (строка), instagram_post (строка), '
            'article_title (строка), article_markdown (строка 500-900 слов), '
            'fact_check (строка, что проверять).\n'
            'Слайд 1: сильный конкретный хук; 2-3: проблема; 4-6: практика с примером; '
            '7: ограничения и польза; 8: CTA. Никаких выдуманных исследований, кейсов, цифр и гарантий. '
            'Контент для VK, Telegram, Instagram должен различаться. ')


def model_configured():
    return bool(os.getenv('CF_WORKERS_AI_TOKEN') and os.getenv('CF_ACCOUNT_ID'))


def call_workers(prompt):
    token=os.getenv('CF_WORKERS_AI_TOKEN','').strip()
    account=os.getenv('CF_ACCOUNT_ID','').strip()
    if not token or not account:
        raise RuntimeError('Cloudflare Workers AI credentials not configured')
    body={'messages':[{'role':'system','content':'Ты профессиональный русскоязычный редактор. Возвращай строго JSON без markdown.'},
                      {'role':'user','content':prompt}], 'max_tokens':4096, 'temperature':0.65}
    u=f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{MODEL}'
    req=Request(u,data=json.dumps(body,ensure_ascii=False).encode(),method='POST',
                headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'ContentFactory/4.0'})
    try:
        with urlopen(req,timeout=120) as r:
            raw=json.load(r)
    except HTTPError as e:
        raise RuntimeError('Workers AI HTTP '+str(e.code)+' '+e.read(200).decode('utf-8','replace')) from None
    if not raw.get('success'):
        raise RuntimeError('Workers AI failed: '+str(raw.get('errors',[]))[:250])
    txt=raw.get('result',{}).get('response','')
    if isinstance(txt,list):
        txt=''.join(str(p.get('text','')) for p in txt if isinstance(p,dict))
    txt=str(txt).strip()
    if txt.startswith('```'):
        txt=re.sub(r'^```(?:json)?\s*','',txt,flags=re.I)
        txt=re.sub(r'\s*```$','',txt)
    try:
        result=json.loads(txt)
    except ValueError:
        a,b=txt.find('{'),txt.rfind('}')
        if a<0 or b<=a:
            raise RuntimeError('Модель не вернула JSON; сохранён не был') from None
        result=json.loads(txt[a:b+1])
    validate_pack(result)
    return result


def validate_pack(p):
    if not isinstance(p,dict) or not isinstance(p.get('slides'),list) or len(p['slides'])!=8:
        raise ValueError('Нужно ровно 8 слайдов')
    for i,s in enumerate(p['slides'],1):
        if not isinstance(s,dict) or not all(isinstance(s.get(k),str) and s[k].strip() for k in ('headline','body','visual_prompt')):
            raise ValueError('Пустой слайд '+str(i))
    for k in ('title','hook','vk_post','telegram_post','instagram_post','article_title','article_markdown','fact_check'):
        if not isinstance(p.get(k),str) or len(p[k].strip())<3:
            raise ValueError('Нет текстового поля '+k)
    return True


def generate(uid):
    job=task(uid)
    if not model_configured():
        raise RuntimeError('Модель не подключена: задача остаётся в ожидании')
    if job['status'] not in ('waiting_for_model','error'):
        raise ValueError('Для задачи генерация уже выполнена или запущена')
    with con() as c:
        c.execute("UPDATE tasks SET status='generating',updated_at=?,error=NULL WHERE id=?",(dt(),uid))
    try:
        payload=call_workers(editorial_prompt(job['topic']))
        with con() as c:
            c.execute("UPDATE tasks SET status='draft',payload=?,updated_at=?,error=NULL WHERE id=?",
                      (json.dumps(payload,ensure_ascii=False),dt(),uid))
    except Exception as e:
        with con() as c:
            c.execute("UPDATE tasks SET status='error',updated_at=?,error=? WHERE id=?",(dt(),str(e)[:450],uid))
        raise


def import_pack(uid, payload):
    validate_pack(payload)
    job=task(uid)
    if job['status'] in ('published','scheduled'):
        raise ValueError('Нельзя заменять опубликованный или запланированный материал')
    with con() as c:
        c.execute("UPDATE tasks SET status='draft',payload=?,updated_at=?,error=NULL WHERE id=?",
                  (json.dumps(payload,ensure_ascii=False),dt(),uid))
    return uid


def approve(uid):
    job=task(uid)
    if job['status']!='draft':
        raise ValueError('Утвердить можно только готовый черновик')
    with con() as c:
        c.execute("UPDATE tasks SET status='approved',updated_at=? WHERE id=?",(dt(),uid))
    return uid


def schedule(uid, when):
    job=task(uid)
    if job['status'] not in ('approved','scheduled'):
        raise ValueError('Сначала утверди материал')
    try:
        parsed=datetime.fromisoformat(when.replace('Z','+00:00'))
        if not parsed.tzinfo:
            raise ValueError
        when=parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        raise ValueError('Дата должна быть ISO 8601 с часовым поясом') from None
    with con() as c:
        c.execute("UPDATE tasks SET status='scheduled',scheduled_at=?,updated_at=? WHERE id=?",(when,dt(),uid))
    return uid


def telegram_post(text):
    token=os.getenv('CF_TG_BOT_TOKEN','')
    channel=os.getenv('CF_TG_CHAT_ID','')
    if not token or not channel:
        raise RuntimeError('Telegram bot/chat not configured')
    # Prevent accidental truncated or partial posts.
    if len(text)>4096:
        raise ValueError('Telegram message too long; edit before publishing')
    req=Request('https://api.telegram.org/bot'+token+'/sendMessage',method='POST',
                data=json.dumps({'chat_id':channel,'text':text,'disable_web_page_preview':True},ensure_ascii=False).encode(),
                headers={'Content-Type':'application/json','User-Agent':'ContentFactory/4.0'})
    try:
        with urlopen(req,timeout=30) as r: response=json.load(r)
    except HTTPError as e:
        raise RuntimeError('Telegram HTTP '+str(e.code)) from None
    if not response.get('ok'):
        raise RuntimeError('Telegram did not confirm publication')
    return str(response['result']['message_id'])


def publish_due():
    if os.getenv('CF_AUTOPOST','0')!='1':
        return 0
    if not (os.getenv('CF_TG_BOT_TOKEN') and os.getenv('CF_TG_CHAT_ID')):
        return 0
    now=dt()
    with con() as c:
        jobs=[dict(r) for r in c.execute("SELECT id,scheduled_at FROM tasks WHERE status='scheduled' AND scheduled_at<=? ORDER BY scheduled_at LIMIT 2",(now,))]
    total=0
    for j in jobs:
        uid=j['id']
        with con() as c:
            sent=c.execute("SELECT status FROM publications WHERE task_id=? AND platform='telegram'",(uid,)).fetchone()
            if sent and sent['status']=='published':
                c.execute("UPDATE tasks SET status='published',updated_at=? WHERE id=?",(dt(),uid))
                continue
            # Claim before calling API to avoid duplicate sends on an uncertain network response.
            if sent and sent['status']=='uncertain':
                continue
            c.execute("INSERT OR REPLACE INTO publications(task_id,platform,status) VALUES(?,'telegram','uncertain')",(uid,))
        try:
            result=telegram_post(task(uid)['payload']['telegram_post'])
            with con() as c:
                c.execute("UPDATE publications SET status='published',remote_id=?,published_at=?,error=NULL WHERE task_id=? AND platform='telegram'",(result,dt(),uid))
                c.execute("UPDATE tasks SET status='published',updated_at=? WHERE id=?",(dt(),uid))
            total+=1
        except Exception as e:
            with con() as c:
                c.execute("UPDATE publications SET error=? WHERE task_id=? AND platform='telegram'",(str(e)[:200],uid))
            # Status remains uncertain, requiring manual investigation before retry.
    return total


def auto_generate_tick():
    # Maximum one automatic text package per UTC day on free tier, opt-in.
    if os.getenv('CF_AUTO_GENERATE','0')!='1' or not model_configured():
        return
    with con() as c:
        processed=c.execute("SELECT COUNT(*) FROM tasks WHERE updated_at>=? AND status IN ('draft','approved','scheduled','published','error')",
                            (datetime.now(timezone.utc).date().isoformat(),)).fetchone()[0]
        if processed>=1:
            return
        job=c.execute("SELECT id FROM tasks WHERE status='waiting_for_model' AND (scheduled_at IS NULL OR scheduled_at<=?) ORDER BY scheduled_at LIMIT 1",
                      (dt(),)).fetchone()
    if job:
        try:generate(job['id'])
        except Exception as e:print('AUTOGENERATE:',type(e).__name__,flush=True)


def supervisor():
    while not STOP.wait(60):
        try:
            auto_generate_tick()
            publish_due()
        except Exception as e:print('SUPERVISOR:',type(e).__name__,flush=True)


def stats():
    with con() as c:
        counts={r['status']:r['n'] for r in c.execute('SELECT status,count(*) n FROM tasks GROUP BY status')}
    return {'ok':True,'time':dt(),'model_configured':model_configured(),'model':MODEL,
            'autopost_enabled':os.getenv('CF_AUTOPOST','0')=='1',
            'autogenerate_enabled':os.getenv('CF_AUTO_GENERATE','0')=='1',
            'telegram_configured':bool(os.getenv('CF_TG_BOT_TOKEN') and os.getenv('CF_TG_CHAT_ID')),
            'counts':counts}


UI=r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Content Factory OS 4.0</title><style>
:root{font-family:Inter,system-ui,Arial,sans-serif;color-scheme:dark;background:#0e1119;color:#e8edf5}
*{box-sizing:border-box}body{margin:0;padding:20px;max-width:1150px;margin-inline:auto}h1{font-size:25px;margin:0 0 4px}h2{font-size:18px;margin:0 0 12px}small,.muted{color:#9faabe}button{cursor:pointer;border:0;background:#b7ff73;color:#142119;border-radius:9px;padding:10px 14px;font-weight:700}.second{background:#2d3442;color:white}.wrap{display:grid;grid-template-columns:1.15fr 1fr;gap:16px}.panel{background:#181e2a;padding:18px;border:1px solid #303a4a;border-radius:14px;margin-top:15px}.row{display:flex;gap:10px;align-items:center;justify-content:space-between}input,textarea,select{background:#0e131c;border:1px solid #3a475b;color:#fff;border-radius:8px;padding:10px;width:100%;font:inherit}textarea{min-height:120px}a{color:#b7ff73}.job{width:100%;margin:7px 0;text-align:left;background:#252d3a;color:white;padding:12px;border:1px solid #3a475b;border-radius:8px}.job:hover{border-color:#b7ff73}.tag{font-size:11px;background:#394559;padding:4px 7px;border-radius:6px;color:#dce7f7}.slide{background:#111b2a;border-radius:7px;padding:15px;margin-bottom:8px}.slide b{color:#b7ff73}.warn{background:#3d3023;border:1px solid #80643b;padding:10px;border-radius:9px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}pre{white-space:pre-wrap;word-break:break-word}#detail{max-height:700px;overflow:auto}@media(max-width:800px){.wrap,.grid{grid-template-columns:1fr}}
</style></head><body><div class="row"><div><h1>Content Factory OS 4.0</h1><small>ИИ, контент, сценарии, очередь, контроль публикаций</small></div><span id="health" class="tag">загрузка</span></div>
<div class="warn" style="margin-top:16px">Это локальная панель. Пока модель не подключена, задачи ставятся в очередь; этот чат может подготовить JSON-черновик для импорта. Публикация требует утверждения.</div>
<div class="wrap"><div><section class="panel"><h2>Команды и задачи</h2><input id="topic" placeholder="Тема: как делегировать рутину агенту"><div style="margin:10px 0;display:flex;gap:10px"><button onclick="create()">Добавить задачу</button><button class="second" onclick="reload()">Обновить</button></div><div class="muted">Возможность автоматической генерации появится после подключения Workers AI.</div></section>
<section class="panel"><h2>Контент-план · 30 задач</h2><div id="tasks"></div></section></div>
<div><section class="panel"><h2>AI-агенты · зоны ответственности</h2><div id="agents"></div></section>
<section class="panel"><h2>Содержание / утверждение</h2><div id="detail" class="muted">Выбери задачу слева.</div></section></div></div>
<script>
const $=id=>document.getElementById(id); const safe=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,payload){let o={};if(payload!==undefined){o={method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}}let r=await fetch(path,o),d=await r.json();if(!r.ok)throw new Error(d.error||r.status);return d}
async function reload(){try{let s=await api('/api/status');$('health').textContent='ИИ: '+(s.model_configured?'подключён':'ожидание')+' · TG: '+(s.telegram_configured?'есть':'нет');let a=await api('/api/state');$('agents').innerHTML=a.agents.map(x=>'<div style="padding:7px;border-bottom:1px solid #313949"><b>'+safe(x.title)+'</b><div class="muted">'+safe(x.responsibility)+'</div></div>').join('');$('tasks').innerHTML=a.tasks.map(x=>'<button class="job" onclick="show(\''+x.id+'\')"><span class="tag">'+safe(x.status)+'</span> '+safe(x.rubric)+'<div>'+safe(x.topic)+'</div><small>'+safe(x.scheduled_at||'Без даты')+'</small></button>').join('')}catch(e){alert(e.message)}}
async function create(){try{let r=await api('/api/tasks',{topic:$('topic').value});$('topic').value='';alert('Задача создана: '+r.id);reload()}catch(e){alert(e.message)}}
async function show(id){try{let d=await api('/api/tasks/'+id);let p=d.payload;let out='<b>'+safe(d.topic)+'</b><p>Статус: '+safe(d.status)+'</p><button class="second" onclick="copyPrompt(\''+id+'\')">Копировать промпт для ChatGPT</button>';if(p){out+='<h3>'+safe(p.title)+'</h3><a href="/api/export/'+id+'" target="_blank">Скачать ZIP (8 SVG + тексты)</a><div class="grid">'+p.slides.map((s,i)=>'<div class="slide"><img style="max-width:100%;border-radius:8px" loading="lazy" src="/api/slide/'+id+'/'+(i+1)+'"><small>'+safe(s.visual_prompt)+'</small></div>').join('')+'</div><details><summary>VK</summary><pre>'+safe(p.vk_post)+'</pre></details><details><summary>Telegram</summary><pre>'+safe(p.telegram_post)+'</pre></details><details><summary>Instagram</summary><pre>'+safe(p.instagram_post)+'</pre></details><details><summary>Статья</summary><pre>'+safe(p.article_markdown)+'</pre></details>';if(d.status==='draft')out+='<button onclick="approve(\''+id+'\')">Утвердить</button>';if(d.status==='approved')out+='<p>Материал утверждён. Для публикации нужен подключенный канал и расписание.</p>'}else{out+='<p class="muted">Черновик ещё не получен.</p><button onclick="generate(\''+id+'\')">Запустить генерацию (если ИИ подключён)</button><p>Или вставь JSON-результат от ChatGPT:</p><textarea id="importjson" placeholder="{...}"></textarea><button class="second" onclick="doImport(\''+id+'\')">Импортировать JSON</button>'} $('detail').innerHTML=out;window.current=id}catch(e){alert(e.message)}}
async function copyPrompt(id){let d=await api('/api/prompt/'+id);await navigator.clipboard.writeText(d.prompt);alert('Промпт скопирован')}
async function generate(id){try{await api('/api/generate',{id});alert('Запрос генерации завершён');reload();show(id)}catch(e){alert(e.message);reload()}}
async function doImport(id){try{let p=JSON.parse($('importjson').value);await api('/api/import',{id,payload:p});alert('Черновик сохранён');reload();show(id)}catch(e){alert(e.message)}}
async function approve(id){try{await api('/api/approve',{id});alert('Утверждено');reload();show(id)}catch(e){alert(e.message)}}reload();
</script></body></html>'''

class Web(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def response(self,d,code=200,ctype='application/json; charset=utf-8'):
        if isinstance(d,(dict,list)):d=json.dumps(d,ensure_ascii=False)
        data=d.encode('utf-8')
        self.send_response(code)
        for k,v in {'Content-Type':ctype,'Content-Length':str(len(data)),
                    'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                    'Content-Security-Policy':"default-src 'self'; style-src 'unsafe-inline' 'self'; script-src 'unsafe-inline' 'self'; connect-src 'self'; base-uri 'none'"}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(data)
    def handle_api(self):
        path=urlsplit(self.path).path
        try:
            if self.command=='GET':
                if path=='/':return self.response(UI,ctype='text/html; charset=utf-8')
                if path.startswith('/api/slide/'):
                    pieces=path.split('/')
                    if len(pieces)!=5 or not re.fullmatch(r'[a-f0-9]{12}',pieces[3]):
                        raise ValueError('Bad slide path')
                    j=task(pieces[3]);i=int(pieces[4])-1
                    if not j['payload'] or not 0<=i<8:raise ValueError('Slide not ready')
                    return self.response(slide_svg(j['payload'],i,settings()['name']),ctype='image/svg+xml')
                if path.startswith('/api/export/'):
                    uid=path.rsplit('/',1)[-1];j=task(uid);p=j['payload']
                    if not p:raise ValueError('Content not ready')
                    buff=io.BytesIO()
                    with zipfile.ZipFile(buff,'w',zipfile.ZIP_DEFLATED) as z:
                        z.writestr('content.json',json.dumps(p,ensure_ascii=False,indent=2))
                        z.writestr('article.md','# '+p['article_title']+'\n\n'+p['article_markdown'])
                        for k in ('vk_post','telegram_post','instagram_post'):
                            z.writestr(k+'.txt',p[k])
                        for i in range(8):
                            z.writestr(f'carousel/slide_{i+1:02d}.svg',slide_svg(p,i,settings()['name']))
                    data=buff.getvalue()
                    self.send_response(200)
                    self.send_header('Content-Type','application/zip')
                    self.send_header('Content-Disposition',f'attachment; filename="content-{uid}.zip"')
                    self.send_header('X-Content-Type-Options','nosniff')
                    self.send_header('Content-Length',str(len(data)))
                    self.end_headers();self.wfile.write(data)
                    return
                if path=='/api/status':return self.response(stats())
                if path=='/api/state':return self.response({'settings':settings(),'agents':list_agents(),'tasks':list_tasks()})
                if path.startswith('/api/tasks/'):
                    return self.response(task(path.rsplit('/',1)[-1]))
                if path.startswith('/api/prompt/'):
                    j=task(path.rsplit('/',1)[-1]);return self.response({'prompt':editorial_prompt(j['topic'])})
                return self.response({'error':'Not found'},404)
            n=int(self.headers.get('Content-Length',0))
            if not (0<n<=160000):return self.response({'error':'Invalid payload size'},413)
            body=json.loads(self.rfile.read(n))
            if path=='/api/tasks':return self.response({'id':add_task(body.get('topic',''),body.get('rubric','практика'))})
            if path=='/api/import':return self.response({'id':import_pack(str(body.get('id','')),body.get('payload'))})
            if path=='/api/approve':return self.response({'id':approve(str(body.get('id','')))})
            if path=='/api/schedule':return self.response({'id':schedule(str(body.get('id','')),str(body.get('when','')))})
            if path=='/api/generate':
                if not model_configured():return self.response({'error':'Модель не подключена. Скопируй промпт в ChatGPT или настрой Workers AI.'},409)
                return self.response({'ok':bool(generate(str(body.get('id','')))==None)})
            return self.response({'error':'Not found'},404)
        except Exception as e:
            return self.response({'error':str(e)[:280]},400)
    def do_GET(self):self.handle_api()
    def do_POST(self):self.handle_api()


def main():
    init()
    cmd=sys.argv[1] if len(sys.argv)>1 else 'serve'
    if cmd=='init':
        print('FACTORY 4.0 READY, AGENTS:',len(list_agents()),'TASKS:',len(list_tasks()))
    elif cmd=='status':
        print(json.dumps(stats(),ensure_ascii=False,indent=2))
    elif cmd=='list':
        for t in list_tasks():print(t['id'],t['status'],t['topic'])
    elif cmd=='prompt':
        print(editorial_prompt(task(sys.argv[2])['topic']))
    elif cmd=='add':
        print('TASK ID:',add_task(' '.join(sys.argv[2:])))
    elif cmd=='import':
        uid=sys.argv[2]
        p=json.loads(Path(sys.argv[3]).read_text('utf-8'))
        import_pack(uid,p);print('IMPORTED:',uid)
    elif cmd=='approve':
        print('APPROVED:',approve(sys.argv[2]))
    elif cmd=='schedule':
        print('SCHEDULED:',schedule(sys.argv[2],sys.argv[3]))
    elif cmd=='generate':
        generate(sys.argv[2]);print('GENERATED:',sys.argv[2])
    elif cmd=='tick':
        auto_generate_tick()
        print('PUBLISHED:',publish_due())
    elif cmd=='serve':
        # recover jobs interrupted by a crash: no paid request is automatically restarted
        with con() as c:c.execute("UPDATE tasks SET status='error',error='Работа была прервана, требуется повторная генерация' WHERE status='generating'")
        threading.Thread(target=supervisor,daemon=True).start()
        print('Content Factory v4 at http://127.0.0.1:'+str(PORT),flush=True)
        ThreadingHTTPServer((HOST,PORT),Web).serve_forever()
    else:raise SystemExit('Unknown command')

if __name__=='__main__':main()