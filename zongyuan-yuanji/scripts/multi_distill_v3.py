#!/usr/bin/env python3
import requests, json, time
KEY='ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70'
MODEL='ep-20260925170233-g4f7w'
URL='https://ark.cn-beijing.volces.com/api/v3/chat/completions'
q='联邦记忆池如何保证多节点数据一致性？一句话回答'
for attempt in range(2):
    try:
        r=requests.post(URL,headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'},
            json={'model':MODEL,'messages':[{'role':'user','content':q}],'max_tokens':100},timeout=90)
        ans=r.json()['choices'][0]['message']['content']
        print('ok:',ans[:100])
        payload={'key':'multi_model.distill.daily','value':{'date':'2026-10-11','answer':ans,'model':'doubao','n':1}}
        requests.post('https://www.huodouai.com/api/report/truth',headers={'X-DID':'DID-BR-000002','Content-Type':'application/json'},json=payload,timeout=10)
        print('reported')
        break
    except Exception as e:
        print('retry',attempt+1,str(e)[:80])
        time.sleep(3)
