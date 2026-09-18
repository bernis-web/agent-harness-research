import os,sys,json,time,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
name=sys.argv[1]
assert name.startswith('attempt-') and name.replace('-','').isalnum()
OUT=ROOT/name/'evidence'
OUT.mkdir(parents=True,exist_ok=False)
for sub in ['profile','home/AppData/Roaming','home/AppData/Local','temp','downloads']:(OUT/sub).mkdir(parents=True,exist_ok=True)
keys={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','OS','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'}
env={k:v for k,v in os.environ.items() if k.upper() in keys}
env.update(TEMP=str(OUT/'temp'),TMP=str(OUT/'temp'),HOME=str(OUT/'home'),USERPROFILE=str(OUT/'home'),APPDATA=str(OUT/'home/AppData/Roaming'),LOCALAPPDATA=str(OUT/'home/AppData/Local'),HOMEDRIVE=OUT.drive,HOMEPATH=str(OUT/'home')[2:],T1_OUT=str(OUT),T1_REFERENCE="D:/projects/agent-harness-research/experiments/t1-prep/reference/mindmap.html",T1_PLAYWRIGHT='D:/projects/npm-cache/_npx/cbf1b8a072280925/node_modules/playwright-core')
meta={'started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'attempt':name,'output':str(OUT),'envKeys':sorted(env),'noValuesLogged':True,'visibleBrowser':False}
with (ROOT/name/'stdout.txt').open('w',encoding='utf-8') as so,(ROOT/name/'stderr.txt').open('w',encoding='utf-8') as se:
 p=subprocess.Popen(['node',str(ROOT/'execution/run.cjs')],cwd=OUT,env=env,stdout=so,stderr=se,creationflags=subprocess.CREATE_NO_WINDOW)
 meta['driverPid']=p.pid
 (ROOT/name/'execution-meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
 p.wait()
meta.update(driverExitCode=p.returncode,ended=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
(ROOT/name/'execution-meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta))
sys.exit(p.returncode)
