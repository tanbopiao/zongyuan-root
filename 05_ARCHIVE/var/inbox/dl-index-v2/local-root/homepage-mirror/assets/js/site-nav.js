/* 火斗云智AIOS 全站统一导航组件（单源真理）
   用法：在页面 <body> 顶部放置 <div id="site-nav"></div>
   并在 </body> 前 <script src="/assets/js/site-nav.js"></script>
   降级：占位符内可放 <noscript> 纯文本链接。 */
(function(){
  var NAV=[
    {label:"首页",href:"/"},
    {label:"架构",href:"/architecture.html"},
    {label:"引擎",href:"/engines.html"},
    {label:"产品",href:"/products.html"},
    {label:"治理",href:"/governance.html"},
    {label:"定价",href:"/assets/visual/pricing-v1.html"},
    {label:"试用",href:"/trial.html"},
    {label:"资产沉淀",href:"/assets/visual/digital-asset-sop.html"},
    {label:"资产地图",href:"/assets/visual/global-asset-viz-v2.html"},
    {label:"成果",href:"/achievements.html"},
    {label:"闭环控制台",href:"/auto-ops.html"}
  ];
  function current(){
    var p=location.pathname;
    if(p===""||p==="/") return "/";
    if(p.endsWith("index.html")) p=p.slice(0,-"index.html".length);
    return p;
  }
  function isActive(item){
    var c=current();
    if(item.href==="/") return c==="/";
    return c===item.href || c.indexOf(item.href.replace(/^\//,"").replace(/\.html$/,""))===0 && item.href.indexOf(".html")>0;
  }
  function css(){
    return ""+
    "#site-nav{position:sticky;top:0;z-index:9999;backdrop-filter:blur(14px);background:rgba(11,14,20,.9);border-bottom:1px solid #232a3a;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif}"+
    ".snav{max-width:1180px;margin:0 auto;padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}"+
    ".snav-brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;color:#d8dde6;text-decoration:none}"+
    ".snav-logo{width:26px;height:26px;border:1.5px solid #c9a227;border-radius:7px;display:grid;place-items:center;color:#c9a227;font-size:13px;font-weight:800}"+
    ".snav-brand b{color:#e6c75a}"+
    ".snav-links{display:flex;gap:2px;flex-wrap:wrap}"+
    ".snav-links a{padding:7px 11px;font-size:13.5px;color:#7a8499;text-decoration:none;border-radius:8px;transition:.18s}"+
    ".snav-links a:hover{color:#e6c75a;background:rgba(201,162,39,.12)}"+
    ".snav-links a.on{color:#e6c75a;background:rgba(201,162,39,.14)}";
  }
  function render(){
    var host=document.getElementById("site-nav");
    if(!host) return;
    var st=document.createElement("style"); st.textContent=css();
    document.head.appendChild(st);
    var links=NAV.map(function(n){
      return '<a href="'+n.href+'"'+(isActive(n)?' class="on"':'')+'>'+n.label+'</a>';
    }).join("");
    host.innerHTML='<div class="snav">'+
      '<a class="snav-brand" href="/"><span class="snav-logo">火</span><span>火斗云智<b>AIOS</b></span></a>'+
      '<div class="snav-links">'+links+'</div></div>';
  }
  if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",render);}else{render();}
})();
