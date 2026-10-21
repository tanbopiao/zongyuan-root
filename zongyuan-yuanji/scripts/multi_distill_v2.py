#!/usr/bin/env python3
import requests, json, time
KEY='ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70'
MODEL='ep-20260925170233-g4f7w'
URL='https://ark.cn-beijing.volces.com/api/v3/chat/completions'
QS=['什么是缓存命中率？','联邦记忆池的核心价值是什么？']
results=[]
for q in QS:
    for attempt in range(2):
        try:
            r=requests.post(URL,headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'},
                json={'model':MODEL,'messages':[{'role':'user','content':q}],'max_tokens':150},timeout=45)
            ans=r.json()['choices'][0]['message']['content']
            results.append({'q':q,'a':ans})
            print('ok: '+q[:20])
            break
        except Exception as e:
            print('retry '+str(attempt+1)+': '+str(e)[:50])
            time.sleep(2)
payload={'key':'multi_model.distill.daily.+str(int(time.time()))','value':{'date':'2026-10-11','results':results,'n':len(results)}}
requests.post('https://www.huodouai.com/api/report/truth',headers={'X-DID':'DID-BR-000002','Content-Type':'application/json'},json=payload,timeout=10)
print('上报完成，'+str(len(results))+'条')
