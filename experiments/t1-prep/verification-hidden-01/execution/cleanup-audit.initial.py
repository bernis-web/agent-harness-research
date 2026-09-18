import json,pathlib,psutil,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
records=[]
for name in ['model-harness','model-cases','model-harness-review','model-cases-review','model-audit']:
 p=ROOT/name/'model-call.json'
 m=json.loads(p.read_text(encoding='utf-8'))
 records.append({'source':name,'pid':m.get('pid'),'recordedState':m.get('state')})
for source,file,key in [('browser','attempt-01/evidence/chrome-process.json','pid'),('driver','attempt-01/execution-meta.json','driverPid')]:
 m=json.loads((ROOT/file).read_text(encoding='utf-8'));records.append({'source':source,'pid':m[key]})
for r in records:r['pidExists']=psutil.pid_exists(r['pid']) if r['pid'] else None
result={'at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'method':'Exact recorded PID existence check only; no enumeration, no commandlines, no termination','records':records,'browserDriverAbsent':all(not r['pidExists'] for r in records if r['source'] in ['browser','driver'])}
(ROOT/'cleanup-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
