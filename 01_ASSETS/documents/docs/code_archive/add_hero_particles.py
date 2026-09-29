#!/usr/bin/env python3
"""昆仑主页：Hero动态粒子效果"""
INDEX = "/www/wwwroot/www.huodouai.com/kunlun/index.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在Hero背景区域添加canvas
old_hero_bg = """    <div class="hero-background">
      <!-- 视频背景（占位，后续替换为真实视频） -->
      <div class="hero-background-image">
        <!-- 动态粒子效果将通过JS添加 -->
      </div>
    </div>"""

new_hero_bg = """    <div class="hero-background">
      <canvas id="heroParticles" style="position:absolute;inset:0;width:100%;height:100%;z-index:1"></canvas>
      <div class="hero-background-image"></div>
    </div>"""

content = content.replace(old_hero_bg, new_hero_bg)

# 2. 确保hero-content在canvas之上
if "z-index:2" not in content.split(".hero-content")[1].split("}")[0]:
    content = content.replace(
        ".hero-content { position: relative; z-index: 2; text-align: center; max-width: 800px; }",
        ".hero-content { position: relative; z-index: 2; text-align: center; max-width: 800px; }"
    )

# 3. 在</body>前添加粒子JS
particle_js = """
<script>
(function(){
  const canvas = document.getElementById('heroParticles');
  if(!canvas) return;
  const ctx = canvas.getContext('2d');
  let particles = [];
  const COUNT = 60;
  
  function resize(){
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
  }
  resize();
  window.addEventListener('resize', resize);
  
  for(let i=0;i<COUNT;i++){
    particles.push({
      x: Math.random()*canvas.width,
      y: Math.random()*canvas.height,
      r: Math.random()*1.5+0.5,
      vx: (Math.random()-0.5)*0.3,
      vy: (Math.random()-0.5)*0.3,
      alpha: Math.random()*0.5+0.2
    });
  }
  
  function animate(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    particles.forEach(p=>{
      p.x += p.vx; p.y += p.vy;
      if(p.x<0)p.x=canvas.width; if(p.x>canvas.width)p.x=0;
      if(p.y<0)p.y=canvas.height; if(p.y>canvas.height)p.y=0;
      ctx.beginPath();
      ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle = 'rgba(212,175,55,'+p.alpha+')';
      ctx.fill();
    });
    // 连线
    for(let i=0;i<particles.length;i++){
      for(let j=i+1;j<particles.length;j++){
        const dx=particles[i].x-particles[j].x, dy=particles[i].y-particles[j].y;
        const dist=Math.sqrt(dx*dx+dy*dy);
        if(dist<100){
          ctx.beginPath();
          ctx.moveTo(particles[i].x,particles[i].y);
          ctx.lineTo(particles[j].x,particles[j].y);
          ctx.strokeStyle='rgba(212,175,55,'+(0.15*(1-dist/100))+')';
          ctx.lineWidth=0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(animate);
  }
  animate();
})();
</script>
</body>"""

content = content.replace("</body>", particle_js)

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("昆仑主页Hero动态粒子效果已添加")
