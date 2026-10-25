(function(){
  const btn=document.createElement("div");
  btn.innerHTML="💬";
  btn.style.cssText="position:fixed;bottom:20px;right:20px;width:48px;height:48px;border-radius:50%;background:#fff;color:#5b5fc7;display:flex;align-items:center;justify-content:center;font-size:22px;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,.12);z-index:99999;border:1px solid #e8e8e8";
  btn.onclick=()=>{window.location.href="/chat.html"};
  document.body.appendChild(btn);
})();
