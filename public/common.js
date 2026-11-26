'use strict';
const $=id=>document.getElementById(id), $$=s=>Array.from(document.querySelectorAll(s)), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])), brl=v=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v/100), pretty=v=>JSON.stringify(v,null,2), date=v=>v?new Date(v).toLocaleString('pt-BR'):'—';
let noticeTimer;
function toast(v){$('toast').textContent=String(v);$('toast').classList.add('show');clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('toast').classList.remove('show'),4500)}
let queue=Promise.resolve();
function call(project,action,data){const run=async()=>{const key='portfolio-suite-public-v3:'+project;let snapshot=null;try{snapshot=JSON.parse(localStorage.getItem(key)||'null')}catch{};const response=await fetch('/api/workspace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project,action,data:data||{},snapshot})});let value;try{value=await response.json()}catch{throw Error('O servidor não devolveu uma resposta válida. Tente novamente.')}if(!response.ok)throw Error(value.error||'Falha na solicitação.');try{localStorage.setItem(key,JSON.stringify(value.snapshot))}catch{toast('O armazenamento deste navegador está cheio.')};return value.result};const pending=queue.then(run);queue=pending.catch(()=>{});return pending}

function bind(id,fn){$(id).addEventListener('click',async e=>{e.preventDefault();const b=$(id);if(b.disabled)return;b.disabled=true;b.setAttribute('aria-busy','true');try{await fn(e)}catch(err){toast(err?.message||'Não foi possível concluir a operação.')}finally{b.disabled=false;b.removeAttribute('aria-busy');b.dispatchEvent(new Event('workspace:done'))}})}
function parse(id){try{return JSON.parse($(id).value)}catch{throw Error('JSON inválido em '+id)}}
function out(id,value){$(id).textContent=typeof value==='string'?value:pretty(value)}
function download(name,content,type='application/json'){const a=document.createElement('a'),u=URL.createObjectURL(new Blob([content],{type}));a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
function fill(id,items,value,label,selected){const el=$(id);el.innerHTML=items.map(x=>`<option value="${esc(value(x))}"${value(x)===selected?' selected':''}>${esc(label(x))}</option>`).join('');el.syncMenu?.()}
function eventRows(id,selector,fn){$(id).addEventListener('click',async e=>{const b=e.target.closest(selector);if(!b||b.disabled)return;b.disabled=true;try{await fn(b)}catch(err){toast(err.message)}finally{b.disabled=false}})}
function formValues(id){return Object.fromEntries(new FormData($(id)).entries())}
function submit(id,fn){$(id).addEventListener('submit',async e=>{e.preventDefault();const b=$(id).querySelector('[type=submit]');if(b)b.disabled=true;try{await fn(formValues(id))}catch(err){toast(err.message)}finally{if(b)b.disabled=false}})}
function formatLocalDate(d){return new Date(d).toISOString()}
