import json,sys,time,pathlib,importlib.util
p=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('identity',p/'identity.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
now=time.time();record={'pid':123,'driverPid':456,'exe':'C:/Program Files/Google/Chrome/Application/chrome.exe','profile':'D:/projects/test-owned-profile','spawnBeforeMs':now*1000-20,'spawnAfterMs':now*1000+20}
class Fake:
 def is_running(self):return True
 def exe(self):return record['exe']
 def ppid(self):return 456
 def create_time(self):return now
 def cmdline(self):return ['chrome.exe','--user-data-dir='+record['profile']]
f=Fake();m.psutil.Process=lambda pid:f;m._meta=lambda pid:[{'class':'Chrome_WidgetWin_1','visible':True,'owner':0,'hwnd':321,'pid':pid}]
cases=[]
r=m.verify(record,now);cases.append({'case':'valid-owned','pass':r['targetOwnerHwnd']==321})
try:m.verify(record,now-0.01);cases.append({'case':'identity-reuse','pass':False})
except RuntimeError:cases.append({'case':'identity-reuse','pass':True})
f.exe=lambda:'C:/Windows/not-chrome.exe'
f.cmdline=lambda:(_ for _ in ()).throw(AssertionError('must not read foreign cmdline'))
try:m.verify(record);cases.append({'case':'wrong-exe-before-cmdline','pass':False})
except RuntimeError:cases.append({'case':'wrong-exe-before-cmdline','pass':True})
(p/'identity-tests.json').write_text(json.dumps(cases,indent=2),encoding='utf-8');print(json.dumps(cases));sys.exit(0 if all(x['pass'] for x in cases) else 1)
