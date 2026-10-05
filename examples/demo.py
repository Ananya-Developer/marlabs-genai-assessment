"""Run after both services start. Uses only Python's standard library."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent
BASE = os.getenv('API_URL', 'http://127.0.0.1:8080')
RESPONSES = ROOT / 'responses'
RESPONSES.mkdir(exist_ok=True)


def send(path, content, content_type, caller='atlas-employee-01'):
    headers={'Content-Type':content_type}
    if caller is not None: headers['X-Caller-Id']=caller
    request=Request(BASE+path,data=content,headers=headers,method='POST')
    try:
        with urlopen(request,timeout=20) as response:
            return response.status,json.load(response)
    except HTTPError as response:
        return response.code,json.load(response)


def save(name, response):
    (RESPONSES/name).write_text(json.dumps(response,indent=2)+'\n',encoding='utf-8')


def question(text, caller='atlas-employee-01', day='2026-09-21'):
    return send('/answer',json.dumps({'question':text,'as_of':day}).encode(),'application/json',caller)


def batch(metadata, uploads):
    boundary='marlabs-demo-boundary'
    parts=[]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\nContent-Type: application/json\r\n\r\n'.encode()+json.dumps(metadata).encode()+b'\r\n')
    for name, content in uploads:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+content+b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return send('/batches',b''.join(parts),'multipart/form-data; boundary='+boundary)


if __name__=='__main__':
    for name,text,caller,expected in [
        ('answer.json','certification','atlas-employee-01','ANSWERED'),
        ('conflict.json','home-office','atlas-employee-01','CONFLICT'),
        ('insufficient.json','wellness','atlas-employee-01','INSUFFICIENT_EVIDENCE'),
        ('contractor.json','certification','atlas-contractor-01','ANSWERED'),
        ('boreal.json','certification','boreal-employee-01','ANSWERED')]:
        status,response=question(text,caller)
        assert status==200 and response['status']==expected,(status,response)
        save(name,response)
    status,response=question('certification',None)
    assert status==401,(status,response)
    save('unknown-caller.json',response)
    assert question('certification',day='2026-02-30')[0]==400
    metadata=json.loads((ROOT/'manifest.json').read_text())
    uploads=[(d['filename'],(ROOT/'requests'/d['filename']).read_bytes()) for d in metadata['documents']]
    status,response=batch(metadata,uploads)
    assert status==200,(status,response)
    assert response['summary']=={'total':8,'completed':7,'failed':1},response
    assert response['results'][5]['duplicate_of']=='request-01'
    assert response['results'][1]['policy']['status']=='CONFLICT'
    assert response['results'][1]['extracted']['amount']=='14000'
    assert response['results'][2]['extracted']['amount'] is None
    assert '25000' in response['results'][4]['policy']['answer']
    assert response['results'][4]['extracted']['amount']=='70000'
    assert all(r['review_required'] for r in response['results'])
    save('batch.json',response)
    assert batch(metadata,uploads[:-1])[0]==400
    assert batch(metadata,uploads+[('extra.txt',b'extra')])[0]==400
    assert batch(metadata,uploads+[uploads[0]])[0]==400
    print('Public API demonstration passed; representative JSON saved in examples/responses.')
