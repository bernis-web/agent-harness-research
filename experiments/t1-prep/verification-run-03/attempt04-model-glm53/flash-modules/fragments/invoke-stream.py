import os, sys, subprocess, pathlib, json, time, re, hashlib, threading
ROOT=pathlib.Path(__file__).resolve().parent
MODEL=sys.argv[1]
LIMIT=int(sys.argv[2])
assert MODEL in ('glm-5.3','glm-5.3-flash')
assert 0<LIMIT<=480
args=['D:/projects/node-global/node_modules/@anthropic-ai/claude-code/bin/claude.exe','--print','--safe-mode','--effort','low','--model',MODEL,'--tools','','--disable-slash-commands','--strict-mcp-config','--mcp-config',str(ROOT/'empty-mcp.json'),'--setting-sources','user','--settings',str(ROOT/'settings.json'),'--no-session-persistence','--system-prompt-snapshot','off','--no-chrome','--output-format','stream-json','--verbose','--include-partial-messages']
env=os.environ.copy()
env.update(TEMP=str(ROOT/'temp'),TMP=str(ROOT/'temp'),CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',CLAUDE_CODE_DISABLE_AUTO_MEMORY='1',PYTHONIOENCODING='utf-8')
def scrub(s):
 s=re.sub(r'sk-[A-Za-z0-9_-]{12,}','[REDACTED]',s)
 s=re.sub(r'(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+',r'\1[REDACTED]',s)
 s=re.sub(r'(?i)((?:api[_-]?key|auth[_-]?token|access[_-]?token|password|secret)\s*[=:]\s*)[^\s\"<>]+',r'\1[REDACTED]',s)
 return s
prompt=(ROOT/'prompt.txt').read_text(encoding='utf-8')
meta={'started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'requested_model':MODEL,'timeout_seconds':LIMIT,'args':args,'prompt_sha256':hashlib.sha256(prompt.encode('utf-8')).hexdigest(),'authentication':'normal inherited HOME; no config or credential inspection','output':'sanitized stream-json/stdout and stderr flushed line by line','state':'STARTING'}
def save_meta():
 (ROOT/'model-call.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
save_meta()
start=time.monotonic()
p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',cwd=ROOT,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
meta.update(pid=p.pid,state='RUNNING');save_meta()
models=set();results=[];errors=[]
def pump(stream,filename,parse=False):
 with (ROOT/filename).open('w',encoding='utf-8',buffering=1) as f:
  for raw in iter(stream.readline,''):
   line=scrub(raw);f.write(line);f.flush()
   if parse:
    try:
     ev=json.loads(line)
     if ev.get('model'):models.add(ev['model'])
     if isinstance(ev.get('message'),dict) and ev['message'].get('model'):models.add(ev['message']['model'])
     if ev.get('type')=='result':
      results.append(ev)
      (ROOT/'result.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2),encoding='utf-8')
     if ev.get('type')=='error':errors.append(ev)
    except (ValueError,TypeError):pass
 stream.close()
threads=[threading.Thread(target=pump,args=(p.stdout,'stdout.jsonl',True),daemon=True),threading.Thread(target=pump,args=(p.stderr,'stderr.txt',False),daemon=True)]
for t in threads:t.start()
p.stdin.write(prompt);p.stdin.close()
try:
 p.wait(timeout=LIMIT)
 meta['state']='EXITED'
except subprocess.TimeoutExpired:
 meta['state']='TIMEOUT';meta['error']='bounded task timeout'
 p.kill();p.wait(timeout=10)
 meta['terminated_exact_pid']=p.pid
for t in threads:t.join(timeout=5)
meta.update(ended=time.strftime('%Y-%m-%dT%H:%M:%S%z'),elapsed_seconds=round(time.monotonic()-start,3),exit_code=p.returncode,observed_models=sorted(models),result_received=bool(results),output_threads_finished=all(not t.is_alive() for t in threads))
if results:
 r=results[-1];meta.update(result_is_error=r.get('is_error'),result_subtype=r.get('subtype'),usage=r.get('usage'),modelUsage=r.get('modelUsage'),result_text=r.get('result','') if len(r.get('result',''))<500 else '[see result.json]')
if errors:meta['errors']=errors
save_meta()
print(json.dumps({k:meta.get(k) for k in ['state','requested_model','observed_models','elapsed_seconds','exit_code','result_received','result_is_error','result_text']},ensure_ascii=False))
