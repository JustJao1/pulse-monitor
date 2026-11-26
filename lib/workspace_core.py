"""Loopback-only HTTP workspace. Maintainer: João Victor da Silva (JustJao1)."""
import argparse,base64,csv,datetime as dt,io,json,mimetypes,os,re,threading,time,urllib.parse,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from engine import *
ROOT=Path(__file__).resolve().parent

class Workspace:
    def __init__(self,path,port):self.store=Store(path);self.store.seed();self.port=port;self.stop=threading.Event();self.monitor_lock=threading.Lock();self.flow_lock=threading.Lock()
    def state(self,p):
        kinds=["monitors","checks","incidents"]
        data={k:self.store.list(p,k) for k in kinds};
        return data
    def check(self,i):
        with self.monitor_lock:
            s=self.store;m=s.get('pulse','monitors',i)
            try:r=http_call(m['url'],port=self.port)
            except Exception as e:r={'status':0,'ms':0,'error':str(e)}
            ok=r['status']==m['expected'];check=s.put('pulse','checks',{'monitor':i,'status':r['status'],'ms':r['ms'],'ok':ok,'error':r.get('error','')});s.trim('pulse','checks',1000)
            with s.lock:
                m=s.get('pulse','monitors',i);m['last_run']=time.time();s.put('pulse','monitors',m)
                opened=next((a for a in s.list('pulse','incidents') if a['monitor']==i and not a.get('closed')),None)
                if not ok and not opened:s.put('pulse','incidents',{'monitor':i,'name':m['name'],'status':r['status'],'closed':None})
                elif ok and opened:opened['closed']=stamp();s.put('pulse','incidents',opened)
            return check
    def action(self,p,a,d):
        s=self.store;d=obj(d)
        if p=='pulse':
            if a=='save':
                url=text(d.get('url'),2000);need(url.startswith('/sample/') or urllib.parse.urlsplit(url).scheme in ('http','https'),'URL inválida.');m={'name':text(d.get('name'),120),'url':url,'interval':whole(d.get('interval'),15,86400),'expected':whole(d.get('expected',200),100,599),'enabled':bool(d.get('enabled',True)),'last_run':0};
                if d.get('id'):prior=s.get(p,'monitors',d['id']);m.update(id=prior['id'],created=prior['created'],last_run=prior.get('last_run',0))
                return s.put(p,'monitors',m)
            if a=='check':return self.check(d['id'])
            if a=='toggle':m=s.get(p,'monitors',d['id']);m['enabled']=not m['enabled'];return s.put(p,'monitors',m)
            if a=='delete':s.remove(p,'monitors',d['id']);return {'ok':True}
        raise ValueError('Operação desconhecida.')
