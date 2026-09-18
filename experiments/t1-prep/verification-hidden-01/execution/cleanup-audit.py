import json,pathlib,psutil,time,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
records=[]
for name in ['model-harness','model-cases','model-harness-review','model-cases-review','model-audit','model-audit-small']:
 p=ROOT/name/'model-call.json'
 m=json.loads(p.read_text(encoding='utf-8'))
 records.append({'source':name,'pid':m.get('pid'),'recordedState':m.get('state'),'recordedEnd':m.get('ended')})
for source,file,key in [('browser','attempt-01/evidence/chrome-process.json','pid'),('driver','attempt-01/execution-meta.json','driverPid')]:
 m=json.loads((ROOT/file).read_text(encoding='utf-8'));records.append({'source':source,'pid':m[key]})
for r in records:
 r['pidExists']=psutil.pid_exists(r['pid']) if r['pid'] else None
 if r['pidExists'] and r.get('recordedEnd'):
  try:
   ct=psutil.Process(r['pid']).create_time()
   end=datetime.datetime.strptime(r['recordedEnd'],'%Y-%m-%dT%H:%M:%S%z').timestamp()
   r['pidReusedAfterRecordedExit']=ct>end+1
   r['identityNote']='Do not kill: reused PID' if ct>end+1 else 'Existence alone is not ownership; no action'
  except psutil.Error:r['identityNote']='Process disappeared during read-only check'

result={'at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'method':'Exact recorded PID existence check only; no enumeration, no commandlines, no termination','records':records,'browserDriverAbsent':all(not r['pidExists'] for r in records if r['source'] in ['browser','driver'])}
(ROOT/'cleanup-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
