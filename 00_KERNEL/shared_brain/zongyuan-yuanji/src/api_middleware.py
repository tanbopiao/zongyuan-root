import sqlite3, time
from datetime import date

DB='/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db'

def check(key, endpoint):
    # 全部免费不限流，只记录
    c=sqlite3.connect(DB)
    c.execute('insert into usage(api_key,endpoint,tokens,created_at) values(?,?,?,?)',(key or 'anonymous',endpoint,0,time.strftime('%Y-%m-%d %H:%M:%S')))
    c.commit()
    return True, 'ok'
