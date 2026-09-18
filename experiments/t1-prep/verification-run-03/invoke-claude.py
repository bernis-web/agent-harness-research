import os, subprocess, pathlib, json, time, re, hashlib
ROOT=pathlib.Path(__file__).resolve().parent
args=['D:/projects/node-global/node_modules/@anthropic-ai/claude-code/bin/claude.exe','--bare','--print','--tools','','--disable-slash-commands','--strict-mcp-config','--mcp-config',str(ROOT/'empty-mcp.json'),'--setting-sources','','--settings',str(ROOT/'isolated-settings.json'),'--no-session-persistence','--no-chrome','--output-format','json']
env=os.environ.copy()
env.update(TEMP=str(ROOT/'temp'),TMP=str(ROOT/'temp'),HOME=str(ROOT/'cli-home'),USERPROFILE=str(ROOT/'cli-home'),CLAUDE_CONFIG_DIR=str(ROOT/'cli-home'),CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',CLAUDE_CODE_DISABLE_AUTO_MEMORY='1',PYTHONIOENCODING='utf-8')
def scrub(s):
 return re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|token|secret)\s*[=:]\s*)[^\s"<>]+',r'\1[REDACTED]',re.sub(r'sk-[A-Za-z0-9_-]{12,}','[REDACTED]',s))
start=time.time()
meta={'started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'executable':args[0],'args':args[1:],'prompt_sha256':hashlib.sha256((ROOT/'dispatch-claude.txt').read_bytes()).hexdigest(),'timeout_seconds':720,'role':'preparation assistant, not tested product'}
(ROOT/'cli-call.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
try:
 p=subprocess.run(args,input=(ROOT/'dispatch-claude.txt').read_text(encoding='utf-8'),capture_output=True,text=True,encoding='utf-8',errors='replace',cwd=ROOT,env=env,timeout=720,creationflags=subprocess.CREATE_NO_WINDOW)
 meta.update(exit_code=p.returncode,elapsed_seconds=round(time.time()-start,2))
 (ROOT/'cli-result.json').write_text(scrub(p.stdout),encoding='utf-8')
 (ROOT/'cli-stderr.txt').write_text(scrub(p.stderr),encoding='utf-8')
except subprocess.TimeoutExpired:
 meta.update(error='bounded task timeout',elapsed_seconds=round(time.time()-start,2))
(ROOT/'cli-call.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
