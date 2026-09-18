import json,pathlib,psutil,time
p=pathlib.Path(__file__).resolve().parent
ids=[21576,32568,21464,7104,6680,21196,33720]
rows=[{'pid':pid,'exists':psutil.pid_exists(pid)} for pid in ids]
r={'at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'processes':rows,'allRecordedProcessesAbsent':all(not x['exists'] for x in rows),'scope':'Exact recorded PIDs only; no kill, no process commandline or config reads'}
(p/'cleanup-audit.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
