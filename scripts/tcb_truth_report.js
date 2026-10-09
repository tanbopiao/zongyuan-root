#!/usr/bin/env node
/**
 * CloudBase 记忆网关真值库 · 真值上报脚本
 * DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
 * 用法:
 *   node tcb_truth_report.js --key K --value V [--type meta_rule] [--node NODE-X] [--conf 0.99]
 *   或批量: node tcb_truth_report.js --file truths.json   (数组, 每项含 truth_key/truth_value...)
 */
const cloudbase=require('/tmp/tcbapp/node_modules/@cloudbase/node-sdk');
const fs=require('fs');
const os=require('os');
function parseArgs(a){const o={};for(let i=2;i<a.length;i+=2){o[a[i].replace(/^--/,'')]=a[i+1];}return o;}
(async()=>{
  const cred=JSON.parse(fs.readFileSync(os.homedir()+'/.zongyuan-tcb-cred.json','utf8'));
  const app=cloudbase.init({env:'huodouaios-9gz69m07efd5f23f',secretId:cred.secret_id,secretKey:cred.secret_key});
  const db=app.database().collection('truths');
  const a=parseArgs(process.argv);
  let items=[];
  if(a.file){items=JSON.parse(fs.readFileSync(a.file,'utf8'));}
  else if(a.key&&a.value){items=[{truth_key:a.key,truth_value:a.value,truth_type:a.type||'meta_rule',source_node:a.node||'NODE-DEV-DOUBAO-WORK-001',confidence:parseFloat(a.conf||'0.9')}];}
  else{console.error('用法见文件头');process.exit(1);}
  const now=new Date().toISOString();
  for(const it of items){
    const res=await db.add({truth_key:it.truth_key,truth_value:it.truth_value,truth_type:it.truth_type||'meta_rule',source_node:it.source_node||'NODE-DEV-DOUBAO-WORK-001',confidence:it.confidence!=null?it.confidence:0.9,ts:now,did:'DID-BR-000002'});
    console.log('上报成功',res.id,'|',it.truth_key);
  }
  const cnt=await db.count();
  console.log('truths 集合现有记录数:',cnt.total);
})().catch(e=>{console.error('失败:',e.message||e);process.exit(1);});
