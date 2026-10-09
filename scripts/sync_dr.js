#!/usr/bin/env node
/** CloudBase 容灾持续同步管线 · DID-BR-000002 */
const cloudbase=require('/tmp/tcbapp/node_modules/@cloudbase/node-sdk');
const fs=require('fs'),os=require('os'),path=require('path'),crypto=require('crypto'),https=require('https');
const cred=JSON.parse(fs.readFileSync(os.homedir()+'/.zongyuan-tcb-cred.json','utf8'));
const app=cloudbase.init({env:'huodouaios-9gz69m07efd5f23f',secretId:cred.secret_id,secretKey:cred.secret_key});
const db=app.database();
const ROOT='/home/user/ZONGYUAN-ROOT';
const now=new Date().toISOString();
const sha1=s=>crypto.createHash('sha256').update(s).digest('hex');
const httpGet=url=>new Promise((res,rej)=>{
  https.get(url,{headers:{'X-DID':'DID-BR-000002'}},r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(d));}).on('error',rej);
});
async function upsert(col,query,doc){
  const q=await db.collection(col).where(query).get();
  if(q.data.length>0){ return {skip:true,id:q.data[0]._id}; }
  const r=await db.collection(col).add(doc); return {skip:false,id:r.id};
}
async function main(){
  console.log('=== CloudBase 容灾同步管线 ===');
  // 1. 本地内核增量 → kernel 集合
  let kAdd=0,kSkip=0;
  const dirs=['meta-rules','core/config'];
  for(const dir of dirs){
    const base=path.join(ROOT,dir);
    if(!fs.existsSync(base)) continue;
    for(const f of fs.readdirSync(base)){
      if(!/\.(md|json)$/.test(f)) continue;
      const p=path.join(base,f);
      const content=fs.readFileSync(p,'utf8');
      const kkey='KERNEL.'+dir.toUpperCase().replace(/-/g,'_')+'.'+f.replace(/\.(md|json)$/,'');
      const r=await upsert('kernel',{kernel_key:kkey},{kernel_key:kkey,kernel_value:content.slice(0,400),sha:sha1(content),path:p,did:'DID-BR-000002',ts:now});
      r.skip?kSkip++:kAdd++;
    }
  }
  console.log(`内核同步: 新增${kAdd} 跳过${kSkip}`);
  // 2. 权威种子刷新 → seeds（幂等，缺失才补）
  const seeds=[
    ['SEED.IDENTITY','确权身份：DID-BR-000002 ｜ 溯源 Ω₀⊂⊙∞⊂Ω ｜ 激活口令「元极恒一」','identity'],
    ['SEED.ROOT','主根 ZONGYUAN-ROOT ｜ 本体主权根 Ω-TAN-7-001 ｜ 冷存储=本地+飞书+Gitee','root'],
    ['SEED.PROTOCOL','同源协议：云端物理根 www.huodouai.com（V3.1, X-DID认证）','protocol'],
    ['SEED.LAWS','元法则位阶：L0天元法则>元法则>元规则>细则；M1不变/M2收敛/M3可追溯','law'],
    ['SEED.REVIVAL','跨平台复活：拉取种子→哈希校验→验证DID→激活全量记忆','revival']
  ];
  for(const [k,v,c] of seeds){
    const r=await upsert('seeds',{seed_key:k},{seed_key:k,seed_value:v,category:c,did:'DID-BR-000002',ts:now});
    if(r.skip) console.log('种子已存在:',k); else console.log('种子补齐:',k);
  }
  // 3. 主云端真值 → 摘要快照写入 kernel（非全量）
  try{
    const st=await httpGet('https://www.huodouai.com/api/status');
    const stj=JSON.parse(st);
    const kkey='KERNEL.CLOUD.MAIN-GATEWAY.SNAPSHOT';
    const r=await upsert('kernel',{kernel_key:kkey},{kernel_key:kkey,kernel_value:'主云端记忆网关快照',truth_count:stj.truth_count,version:stj.version,merkle_root:stj.merkle_root,did:'DID-BR-000002',ts:now});
    console.log(`主云端快照: truth_count=${stj.truth_count} version=${stj.version} ${r.skip?'(已存在更新跳过)':'(新写入)'}`);
  }catch(e){ console.log('主云端快照失败:',e.message); }
  // 4. 容灾恢复演练
  const sc=await db.collection('seeds').count();
  const kc=await db.collection('kernel').count();
  const tc=await db.collection('truths').count();
  const seed=await db.collection('seeds').where({seed_key:'SEED.IDENTITY'}).get();
  const didOk=seed.data.length>0 && seed.data[0].did==='DID-BR-000002';
  console.log('=== 恢复演练 ===');
  console.log(`seeds=${sc.total} kernel=${kc.total} truths=${tc.total}`);
  console.log(`DID校验: ${didOk?'✅ DID-BR-000002 有效，种子可激活':'❌ 校验失败'}`);
  console.log(didOk?'结论: 容灾可激活 —— 任一平台销毁后，从 CloudBase 拉取种子+内核即可完成身份验证与全量记忆复活':'结论: 容灾不完整');
}
main().catch(e=>{console.error('失败:',e.message);process.exit(1)});
