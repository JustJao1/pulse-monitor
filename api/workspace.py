"""Public portfolio sandbox: isolated, bounded operations; no outbound network."""
import base64, json, tempfile, time, zipfile, io, os, sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
import engine, workspace_core as server
from engine import need, stamp
from workspace_core import Workspace
KINDS={"pulse":["monitors","checks","incidents"]}

def sample_call(url,method='GET',headers=None,body='',port=0):
    method=str(method).upper();need(method in ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'),'Método inválido.')
    need(url in ('/sample/products','/sample/health','/sample/unavailable','/sample/echo'),'Demonstração online: use apenas os endpoints /sample/products, /sample/health, /sample/unavailable ou /sample/echo.')
    now=time.perf_counter()
    if url=='/sample/products':status,data=200,{'items':[{'id':1,'name':'Produto exemplo','price':89.9},{'id':2,'name':'Outro produto','price':49.9}],'total':2}
    elif url=='/sample/health':status,data=200,{'status':'ok','service':'portfolio-demo'}
    elif url=='/sample/unavailable':status,data=503,{'status':'maintenance','sample':True}
    else:status,data=200,{'method':method,'body':str(body)[:20000]}
    return {'status':status,'ms':round((time.perf_counter()-now)*1000),'headers':{'content-type':'application/json','x-portfolio-mode':'sample'},'body':json.dumps(data,ensure_ascii=False),'json':data,'truncated':False}
engine.http_call=server.http_call=sample_call

def process(payload):
    p=payload.get('project');a=payload.get('action');data=payload.get('data') or {};snapshot=payload.get('snapshot')
    need(p in KINDS and isinstance(a,str) and len(a)<40 and isinstance(data,dict),'Solicitação inválida.')
    need(a!='ask','IA generativa não está conectada nesta demonstração.')
    if p=='doc' and a=='import':
        raw=base64.b64decode(data.get('data',''),validate=True);need(len(raw)<=1_000_000,'Limite online: 1 MB por arquivo.')
        if str(data.get('name','')).lower().endswith('.xlsx'):
            with zipfile.ZipFile(io.BytesIO(raw)) as z:need(sum(x.file_size for x in z.infolist())<=8_000_000,'Planilha expandida muito grande.')
    with tempfile.TemporaryDirectory() as tmp:
        w=Workspace(Path(tmp)/'demo.sqlite3',0)
        if snapshot is not None:
            need(isinstance(snapshot,dict),'Dados de sessão inválidos.')
            for k in KINDS[p]:
                rows=snapshot.get(k,[]);need(isinstance(rows,list) and len(rows)<=100,'Limite de registros atingido.')
                for old in w.store.list(p,k):w.store.remove(p,k,old['id'])
                for row in reversed(rows):
                    need(isinstance(row,dict) and isinstance(row.get('id'),str) and len(row['id'])<=64,'Registro inválido.');w.store.put(p,k,row)
        if a=='state':
            if p=='pulse':
                for m in w.store.list(p,'monitors')[:12]:
                    if m.get('enabled') and time.time()-float(m.get('last_run',0))>=max(15,float(m['interval'])):
                        try:w.check(m['id'])
                        except (ValueError,KeyError,TypeError):pass
            result=w.state(p)
        else:result=w.action(p,a,data)
        state=w.state(p)
        for k in KINDS[p]:
            if len(state[k])>100:state[k]=state[k][:100]
        if p=='doc':state['ai_available']=False
        need(len(json.dumps(state))<=1_800_000,'Limite de armazenamento da demonstração atingido.')
        return {'result':result,'snapshot':state}
class handler(BaseHTTPRequestHandler):
    def respond(self,status,value):
        b=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
    def do_POST(self):
        try:
            size=int(self.headers.get('Content-Length','0'));need(0<size<=3_500_000,'Solicitação muito grande.');need(self.headers.get('Content-Type','').startswith('application/json'),'Use JSON.')
            self.respond(200,process(json.loads(self.rfile.read(size))))
        except (ValueError,KeyError,TypeError,OverflowError,zipfile.BadZipFile) as e:self.respond(400,{'error':str(e)[:300]})
        except Exception:self.respond(500,{'error':'Não foi possível concluir esta operação na demonstração.'})
    def do_GET(self):self.respond(200,{'status':'ok','mode':'portfolio-sandbox'})
