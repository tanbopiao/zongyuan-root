#!/usr/bin/env python3
"""DID自动注册：新AI接入自动分配编号"""
import sqlite3, secrets, json, time

DB='/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db'
ADMIN_DID='DID-BR-000002'

def register_node(name='unknown'):
    """自动注册新节点DID"""
    node_id='DID-NODE-'+secrets.token_hex(3).upper()
    c=sqlite3.connect(DB)
    c.execute("insert into truth(key,value,ts,event_id) values(?,?,?,?)",
        (f'NODE.REG.{node_id}',json.dumps({'name':name,'level':'public','registered':time.strftime('%Y-%m-%dT%H:%M:%S%z')}),int(time.time()),'auto-register'))
    c.commit();c.close()
    return node_id

def get_level(did):
    """查DID权限等级"""
    if did==ADMIN_DID: return 'admin'
    c=sqlite3.connect(DB)
    r=c.execute("select value from truth where key=?",(f'NODE.REG.{did}',)).fetchone()
    c.close()
    if r: return json.loads(r[0]).get('level','public')
    return 'public'

if __name__=='__main__':
    print('注册测试:', register_node('codearts-test'))
    print('管理员权限:', get_level(ADMIN_DID))
