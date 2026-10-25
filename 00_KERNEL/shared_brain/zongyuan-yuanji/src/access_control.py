#!/usr/bin/env python3
"""三级权限：public(任何人可读)/internal(带DID头可读)/secret(带密钥可读)"""

SECRET_KEYS = ['SECRET','API_KEY','PASSWORD','SSH.CRED','TOKEN','PRIVATE']

def classify(key, value=''):
    k = key.upper()
    for s in SECRET_KEYS:
        if s in k:
            return 'secret'
    if k.startswith(('WORK.','TRUTH.','CLOUD.','DEPLOY.','KERNEL.','META.')):
        return 'internal'
    return 'public'

def can_read(level, auth_header=''):
    if level == 'public': return True
    if level == 'internal': return bool(auth_header)  # 带X-DID头
    if level == 'secret': return auth_header == 'Bearer sk-admin-zongyuan'  # 管理员密钥
    return False

if __name__=='__main__':
    tests=[('WORK.LEDGER.1',''),('TRUTH.CLOUD.1',''),('API_KEY.ark-123',''),('普通条目','')]
    for k,_ in tests:
        l=classify(k)
        print(f'{k:25s} → {l}')
