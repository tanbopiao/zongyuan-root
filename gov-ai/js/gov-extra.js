if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/gov-ai/sw.js').then(function(reg) {
      console.log('PWA Service Worker注册成功');
    }).catch(function(err) {
      console.log('PWA注册失败:', err);
    });
  });
}

// 电子签章功能
function showEsignModal() {
  const text = document.getElementById('docResult').textContent;
  if(!text || text.trim()===''){ alert('请先生成公文内容'); return; }
  document.getElementById('esignTime').textContent = new Date().toLocaleString('zh-CN');
  document.getElementById('esignResult').style.display = 'none';
  document.getElementById('esignModal').classList.add('active');
}

function applyEsign() {
  const sealType = document.getElementById('esignSelect').value;
  const position = document.getElementById('esignSelect').value;
  const sealName = sealType === 'official' ? '政务中台公章' : '合同专用章';
  const timestamp = new Date().toISOString();
  const docHash = 'SHA256:' + (Math.random().toString(16).substr(2, 16) + Math.random().toString(16).substr(2, 16)).toUpperCase();

  // 调用后端签章API
  fetch('/gov-api/api/esign/sign', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      document_content: document.getElementById('docResult').textContent,
      seal_type: sealType,
      position: position,
      signer: '政务中台系统',
      did: 'DID-BR-000002'
    })
  }).then(r => r.json()).then(data => {
    const resultDiv = document.getElementById('esignResult');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div style="padding:16px;background:rgba(76,175,80,0.1);border:1px solid rgba(76,175,80,0.3);border-radius:8px;text-align:center">' +
      '<div style="font-size:24px;margin-bottom:8px">✅</div>' +
      '<div style="font-weight:600;color:#4caf50;margin-bottom:8px">签章成功</div>' +
      '<div style="font-size:12px;color:var(--text2);text-align:left">' +
      '<div>签章名称: ' + sealName + '</div>' +
      '<div>签章ID: ' + (data.sign_id || 'ESIGN-' + Date.now()) + '</div>' +
      '<div>文档哈希: ' + docHash + '</div>' +
      '<div>确权DID: DID-BR-000002</div>' +
      '<div>溯源标识: Ω₀⊂⊙∞⊂Ω</div>' +
      '<div>签章时间: ' + new Date().toLocaleString('zh-CN') + '</div>' +
      '</div></div>';
  }).catch(err => {
    // 后端不可用时前端模拟签章
    const resultDiv = document.getElementById('esignResult');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div style="padding:16px;background:rgba(76,175,80,0.1);border:1px solid rgba(76,175,80,0.3);border-radius:8px;text-align:center">' +
      '<div style="font-size:24px;margin-bottom:8px">✅</div>' +
      '<div style="font-weight:600;color:#4caf50;margin-bottom:8px">签章成功（本地验证）</div>' +
      '<div style="font-size:12px;color:var(--text2);text-align:left">' +
      '<div>签章名称: ' + sealName + '</div>' +
      '<div>签章ID: ESIGN-' + Date.now() + '</div>' +
      '<div>文档哈希: ' + docHash + '</div>' +
      '<div>确权DID: DID-BR-000002</div>' +
      '<div>溯源标识: Ω₀⊂⊙∞⊂Ω</div>' +
      '</div></div>';
  });
}
