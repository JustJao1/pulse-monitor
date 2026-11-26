"""Pulse Monitor — project owner and maintainer: João Victor da Silva (JustJao1)."""
import base64,csv,datetime as dt,io,ipaddress,json,math,os,re,socket,sqlite3,time,uuid,urllib.request,urllib.error,urllib.parse,threading
from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import Counter
from contextlib import contextmanager
from difflib import unified_diff

CITIES={'São Carlos':(-22.017,-47.891),'Araraquara':(-21.784,-48.176),'Ribeirão Preto':(-21.178,-47.810),'Campinas':(-22.906,-47.061),'São Paulo':(-23.550,-46.633),'Bauru':(-22.314,-49.061),'Sorocaba':(-23.501,-47.458),'Santos':(-23.961,-46.333),'Piracicaba':(-22.725,-47.650),'São José dos Campos':(-23.189,-45.884)}
PROJECTS={'pulse'}
def stamp():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def ident():return uuid.uuid4().hex[:12]
def need(v,msg):
    if not v:raise ValueError(msg)
    return v
def text(v,limit=300):
    s=str(v or '').strip();need(s and len(s)<=limit,'Preencha o campo corretamente.');return s
def num(v,low=0,high=1e9):
    try:x=float(v)
    except (ValueError,TypeError):raise ValueError('Número inválido.')
    need(math.isfinite(x) and low<=x<=high,'Número fora do intervalo permitido.');return x
def cents(v):
    try:x=Decimal(str(v));need(x.is_finite() and 0<=x<=100000000,'Valor inválido.');return int((x*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    except InvalidOperation:raise ValueError('Valor inválido.')
def whole(v,low,high):
    x=num(v,low,high);need(x.is_integer(),'Use um número inteiro.');return int(x)
def obj(v):need(isinstance(v,dict),'Esperado um objeto JSON.');return v
def array(v):need(isinstance(v,list),'Esperada uma lista.');return v
def csv_safe(v):
    s=str(v);return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s

def path_get(v,p):
    if p=='':return v
    for k in p.split('.'):
        if isinstance(v,list) and k.isdigit() and int(k)<len(v):v=v[int(k)]
        elif isinstance(v,dict) and k in v:v=v[k]
        else:raise ValueError('Campo não encontrado: '+p)
    return v

def substitute(s,variables):
    def replace(m):
        k=m.group(1);need(k in variables,'Variável ausente: '+k);return str(variables[k])
    return re.sub(r'\{\{([A-Za-z0-9_]+)\}\}',replace,str(s))

class Store:
    def __init__(self,path):
        self.path=str(path);self.lock=threading.RLock()
        with self.connect() as c:
            c.execute('PRAGMA journal_mode=WAL');c.execute('CREATE TABLE IF NOT EXISTS records (project TEXT, kind TEXT, id TEXT, data TEXT NOT NULL, PRIMARY KEY(project,kind,id))');c.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=15)
        try:
            with c:yield c
        finally:c.close()
    def list(self,p,k):
        with self.connect() as c:return [json.loads(r[0]) for r in c.execute('SELECT data FROM records WHERE project=? AND kind=? ORDER BY rowid DESC',(p,k))]
    def get(self,p,k,i):
        with self.connect() as c:r=c.execute('SELECT data FROM records WHERE project=? AND kind=? AND id=?',(p,k,i)).fetchone()
        if not r:raise ValueError('Registro não encontrado.')
        return json.loads(r[0])
    def put(self,p,k,d):
        d=dict(d);d.setdefault('id',ident());d.setdefault('created',stamp());d['updated']=stamp()
        with self.connect() as c:c.execute('INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(project,kind,id) DO UPDATE SET data=excluded.data',(p,k,d['id'],json.dumps(d,ensure_ascii=False)))
        return d
    def put_many(self,p,items):
        with self.connect() as c:
            for k,d in items:
                d['updated']=stamp()
                c.execute('INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(project,kind,id) DO UPDATE SET data=excluded.data',(p,k,d['id'],json.dumps(d,ensure_ascii=False)))
    def remove(self,p,k,i):
        with self.connect() as c:c.execute('DELETE FROM records WHERE project=? AND kind=? AND id=?',(p,k,i))
    def trim(self,p,k,limit=300):
        with self.connect() as c:c.execute('DELETE FROM records WHERE project=? AND kind=? AND id NOT IN (SELECT id FROM records WHERE project=? AND kind=? ORDER BY rowid DESC LIMIT ?)',(p,k,p,k,limit))
    def seed(self):
        with self.connect() as c:
            if c.execute("SELECT value FROM metadata WHERE key='seed'").fetchone():return
        for name,path in [('Catálogo','/sample/products'),('Serviço de saúde','/sample/health'),('Teste de incidente','/sample/unavailable')]:self.put('pulse','monitors',{'name':name,'url':path,'interval':30,'enabled':True,'expected':200,'last_run':0,'sample':True})
        with self.connect() as c:c.execute("INSERT OR IGNORE INTO metadata VALUES('seed','1')")

def http_call(*args, **kwargs):
    raise ValueError('Only controlled sample endpoints are available.')

def parse_document(name,data):
    ext=Path(name).suffix.lower();need(len(data)<=12_000_000,'Arquivo acima de 12 MB.');pages=[]
    if ext=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data));need(not reader.is_encrypted,'PDF protegido por senha.');need(len(reader.pages)<=150,'Limite de 150 páginas.')
        for i,p in enumerate(reader.pages):pages.append({'page':i+1,'text':(p.extract_text() or '')[:80000]})
    elif ext=='.xlsx':
        from openpyxl import load_workbook
        wb=load_workbook(io.BytesIO(data),read_only=True,data_only=True);need(len(wb.sheetnames)<=30,'Limite de 30 abas.')
        for i,s in enumerate(wb):pages.append({'page':i+1,'text':s.title+'\n'+'\n'.join(' | '.join(str(v or '') for v in row) for row in s.iter_rows(max_row=1000,max_col=40,values_only=True))[:80000]})
        wb.close()
    elif ext in ('.txt','.csv','.md','.json'):pages=[{'page':1,'text':data.decode('utf-8-sig')[:350000]}]
    else:raise ValueError('Formato não suportado. Use PDF, XLSX, TXT, CSV, MD ou JSON.')
    need(any(p['text'].strip() for p in pages),'Nenhum texto extraível. PDFs digitalizados exigem OCR prévio.');return pages

def tokens(s):return re.findall(r'\w{3,}',s.lower(),re.UNICODE)
def search_docs(docs,q):
    words=set(tokens(q));need(words,'Digite ao menos uma palavra com três letras.');hits=[]
    for d in docs:
        for p in d['pages']:
            for i,paragraph in enumerate(re.split(r'\n\s*\n|(?<=\.)\s+(?=[A-ZÁÉÍÓÚ])',p['text'])):
                counts=Counter(tokens(paragraph));score=sum(min(counts[w],3) for w in words)
                if score:hits.append({'id':d['id'],'title':d['title'],'page':p['page'],'section':i+1,'excerpt':paragraph[:1200],'score':score})
    return sorted(hits,key=lambda x:-x['score'])[:25]

def facts(d):
    pattern=r'R\$\s*[\d.]+,\d{2}|\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d+\s+(?:dias?|meses|anos?)\b|\b\d+(?:,\d+)?%'
    return [{'page':p['page'],'value':m[0],'context':p['text'][max(0,m.start()-45):m.end()+55]} for p in d['pages'] for m in re.finditer(pattern,p['text'],re.I)][:300]

def validate_flow(flow):
    ns=array(flow.get('nodes'));need(1<=len(ns)<=50,'Fluxo deve conter de 1 a 50 nós.');ids=[text(n.get('id'),30) for n in ns];need(len(ids)==len(set(ids)),'Identificadores duplicados.');need(flow.get('start') in ids,'Nó inicial inexistente.');lookup={n['id']:n for n in ns}
    for n in ns:
        if 'x' in n:n['x']=num(n['x'],0,3000)
        if 'y' in n:n['y']=num(n['y'],0,2000)
        need(n.get('type') in ('set','condition','http','output','delete','math'),'Tipo de nó inválido.');text(n.get('name'),120)
        for k in ('next','otherwise'):
            if n.get(k):need(n[k] in lookup,'Conexão inexistente.')
    visiting=set();done=set()
    def visit(i):
        if not i or i in done:return
        need(i not in visiting,'Fluxo possui ciclo.');visiting.add(i);n=lookup[i]
        for k in ('next','otherwise'):visit(n.get(k))
        visiting.remove(i);done.add(i)
    for i in ids:visit(i)
    return lookup

def run_flow(flow,payload,port):
    lookup=validate_flow(flow);data=json.loads(json.dumps(obj(payload)));i=flow['start'];trace=[]
    try:
        while i:
            n=lookup[i];typ=n['type'];nxt=n.get('next','');p=n.get('path','');v=n.get('value');start=time.perf_counter()
            if typ in ('set','delete','math'):need(re.fullmatch(r'[\w-]{1,80}',p or ''),'Chave de saída inválida.')
            if typ=='set':data[p]=v
            elif typ=='delete':data.pop(p,None)
            elif typ=='math':data[p]=num(data.get(p,0),-1e9)+num(v,-1e9)
            elif typ=='condition':
                val=path_get(data,p);op=n.get('op','eq');need(op in ('eq','gte','contains'),'Operador inválido.')
                ok=val==v if op=='eq' else num(val,-1e9)>=num(v,-1e9) if op=='gte' else str(v) in str(val)
                if not ok:nxt=n.get('otherwise','')
            elif typ=='http':
                response=http_call(substitute(n.get('url',''),data),n.get('method','GET'),port=port);need(200<=response['status']<300,'HTTP falhou: '+str(response['status']));data[p or 'response']=response['json'] if response['json'] is not None else response['body']
            elif typ=='output':nxt=''
            trace.append({'node':i,'name':n['name'],'type':typ,'next':nxt,'ms':round((time.perf_counter()-start)*1000,2),'state':'ok','data':json.loads(json.dumps(data))});i=nxt
        return {'state':'Concluído','output':data,'trace':trace}
    except Exception as e:return {'state':'Falhou','output':data,'trace':trace+[{'node':i,'name':lookup[i]['name'],'state':'error','error':str(e)}]}

def distance(a,b):
    lat1,lon1=map(math.radians,CITIES[a]);lat2,lon2=map(math.radians,CITIES[b]);x=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2;return round(6371*2*math.asin(min(1,math.sqrt(x))),1)
def profit(p):
    km=num(p.get('km'));cons=num(p.get('consumption'),.1,100);fuel=cents(p.get('fuel'));cost=round(km/cons*fuel)+cents(p.get('tolls',0))+cents(p.get('other',0));gross=cents(p.get('gross'));return {'distance':km,'gross':gross,'cost':cost,'net':gross-cost,'margin':round(100*(gross-cost)/gross,2) if gross else 0,'fuel_liters':round(km/cons,2)}
def check_assertions(res,assertions):
    out=[]
    for a in array(assertions):
        try:
            op=a.get('op');expected=a.get('value');p=a.get('path','')
            if op=='status':actual=res['status'];ok=actual==expected
            elif op=='latency':actual=res['ms'];ok=actual<=num(expected)
            else:
                actual=path_get(res['json'],p)
                if op=='equals':ok=actual==expected
                elif op=='type':actual='null' if actual is None else 'boolean' if isinstance(actual,bool) else 'number' if isinstance(actual,(int,float)) else 'string' if isinstance(actual,str) else 'array' if isinstance(actual,list) else 'object';ok=actual==expected
                elif op=='exists':ok=True
                else:raise ValueError('Operador desconhecido.')
            out.append({'assertion':a,'actual':actual,'pass':ok})
        except Exception as e:out.append({'assertion':a,'pass':False,'error':str(e)})
    return out
