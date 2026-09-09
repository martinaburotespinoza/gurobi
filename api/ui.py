from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"
app = FastAPI()

READABLE_UI = r'''<style id="gurobean-readable-ui">
:root{font-size:16px}
body{font-size:16px!important}
.brand h1{font-size:20px!important}.brand p{font-size:11px!important}
.pill{font-size:13px!important;padding:11px 14px!important}.btn{font-size:13px!important;padding:12px 15px!important}
.mode{font-size:13px!important;padding:11px 15px!important}.eyebrow,.kicker{font-size:12px!important}
.hero p{font-size:15px!important;line-height:1.75!important}.chip{font-size:12px!important;padding:9px 13px!important}
.round{font-size:14px!important;padding:16px 7px!important;min-height:88px!important}.round small{font-size:10px!important}
.title{font-size:24px!important}.desc{font-size:13px!important}.badge{font-size:11px!important}
.field{min-height:124px!important;padding:15px!important}.field label{font-size:13px!important}.field input,.field select,.chat input{font-size:15px!important;padding:13px!important}.field small{font-size:10px!important}
.note{font-size:12px!important}.result-head span{font-size:11px!important}.result{font-size:12px!important;line-height:1.8!important}
.metric{min-height:128px!important;padding:18px!important}.metric small{font-size:10px!important}.metric strong{font-size:30px!important}.metric em{font-size:10px!important}
.side-title h3{font-size:15px!important}.side-title span{font-size:11px!important}.status-line{font-size:13px!important}
.status-card p,.side-section h4{font-size:11px!important}.map-item{font-size:11px!important;padding:11px 5px!important}.map-item span{font-size:9px!important}
.event{font-size:11px!important}.cert b{font-size:13px!important}.cert span{font-size:10px!important}.answer{font-size:11px!important}
.custom-panel label{font-size:11px!important}.custom-panel select{font-size:12px!important}.footer{font-size:10px!important}.toast{font-size:12px!important}
.logo{font-size:0!important;width:58px!important;height:58px!important;border-radius:17px!important;position:relative!important;overflow:visible!important;background:linear-gradient(145deg,#162f4b,#07101e)!important;display:grid!important;place-items:center!important}
.logo:before{content:'☕';font-size:31px;filter:drop-shadow(0 5px 12px rgba(104,220,255,.35));animation:coffeePulse 2.8s ease-in-out infinite;z-index:2}.logo:after{content:'∿  ∿';position:absolute;top:-15px;left:12px;font-size:15px;letter-spacing:3px;color:rgba(242,247,255,.45);animation:steam 2.4s ease-in-out infinite}
@keyframes coffeePulse{0%,100%{transform:translateY(1px) scale(1)}50%{transform:translateY(-3px) scale(1.08)}}@keyframes steam{0%,100%{opacity:.15;transform:translateY(4px)}50%{opacity:.8;transform:translateY(-4px)}}
.round{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:5px!important}.round:after{font-size:25px!important;line-height:1!important;content:'☕';opacity:.9;order:-1;filter:drop-shadow(0 3px 7px rgba(104,220,255,.22))}
.round[data-nav-round="1"]:after{content:'☕'}.round[data-nav-round="2"]:after{content:'🧊'}.round[data-nav-round="3"]:after{content:'📈'}.round[data-nav-round="4"]:after{content:'⚙️'}.round[data-nav-round="5"]:after{content:'👥'}.round[data-nav-round="6"]:after{content:'📦'}.round[data-nav-round="7"]:after{content:'💳'}.round[data-nav-round="8"]:after{content:'🏆'}
.field{background:linear-gradient(145deg,rgba(255,255,255,.04),rgba(104,220,255,.015))!important}.field label:before{content:'◉';color:var(--cyan);margin-right:7px;font-size:12px}
.metric{display:grid!important;grid-template-columns:50px 1fr!important;grid-template-rows:auto auto auto!important;column-gap:12px!important}.metric:before{grid-row:1/4;display:grid;place-items:center;width:50px;height:50px;border-radius:16px;background:rgba(104,220,255,.09);border:1px solid rgba(104,220,255,.16);font-size:27px;content:'☕';animation:metricFloat 3s ease-in-out infinite}.metric:nth-child(2):before{content:'❄️'}.metric:nth-child(3):before{content:'💰'}.metric small,.metric strong,.metric em{grid-column:2}@keyframes metricFloat{50%{transform:translateY(-4px) rotate(-2deg)}}
.result-wrap{box-shadow:inset 0 0 0 1px rgba(104,220,255,.025),0 18px 50px rgba(0,0,0,.2)}.result-head:before{content:'🧠';font-size:20px;margin-right:8px}.result-head{justify-content:flex-start}.result-head span{margin-left:0}.status-line:before{content:'⚡';font-size:19px}.side-section h4:before{margin-right:6px}.side-section:nth-of-type(1) h4:before{content:'📡'}.side-section:nth-of-type(2) h4:before{content:'🗺️'}.side-section:nth-of-type(3) h4:before{content:'✨'}
.event i{width:9px;height:9px;flex-basis:9px}.solve-btn{font-size:15px!important;padding:15px 20px!important;box-shadow:0 16px 38px rgba(65,119,255,.3)!important}.solve-btn:before{content:'☕ ';font-size:19px}.btn.primary:before{content:'✦ ';font-size:15px}.hero:after{content:'☕';position:absolute;right:34%;bottom:-30px;font-size:145px;opacity:.04;filter:blur(.3px);transform:rotate(-12deg);pointer-events:none;animation:heroCup 7s ease-in-out infinite}@keyframes heroCup{50%{transform:rotate(-7deg) translateY(-8px)}}
@media(max-width:760px){.hero p{font-size:14px!important}.hero h2{font-size:40px!important}.round{min-height:78px!important}.metric strong{font-size:27px!important}}@media(max-width:430px){.brand h1{font-size:18px!important}.hero h2{font-size:34px!important}.field input,.field select{font-size:15px!important}.btn,.mode{font-size:13px!important}}
</style>'''

PREMIUM_VISUAL = r'''<style id="gurobean-premium-visual">
/* PREMIUM COFFEE COCKPIT: richer visual hierarchy without touching the solver */
.app{position:relative}
.app:before{content:"";position:fixed;inset:10% 4% auto;max-width:1450px;height:1px;margin:auto;background:linear-gradient(90deg,transparent,rgba(104,220,255,.16),transparent);pointer-events:none}
.hero{min-height:340px!important;border-radius:32px!important}
.hero-copy{max-width:800px!important}
.hero h2{font-weight:800!important;text-shadow:0 10px 45px rgba(0,0,0,.28)}
.hero-visual{filter:drop-shadow(0 24px 50px rgba(47,128,255,.16))}
.toolbar{min-height:58px}
.main-card{padding:20px!important}
.rounds{gap:8px!important}
.round{min-height:104px!important;border-radius:16px!important;background:linear-gradient(180deg,rgba(13,27,45,.9),rgba(5,12,22,.78))!important}
.round:after{font-size:29px!important;filter:drop-shadow(0 5px 12px rgba(104,220,255,.3))}
.round.active{transform:translateY(-2px);box-shadow:0 18px 38px rgba(60,106,240,.22)!important}
.fields{gap:10px!important}
.field{min-height:138px!important;border-radius:16px!important;position:relative;overflow:hidden}
.field:after{content:"";position:absolute;right:-18px;bottom:-28px;width:90px;height:90px;border-radius:50%;background:radial-gradient(circle,rgba(104,220,255,.08),transparent 68%);pointer-events:none}
.field label{font-size:13px!important;letter-spacing:.15px}
.field input,.field select,.chat input{min-height:50px!important;border-radius:12px!important;background:rgba(2,8,16,.82)!important}
.metric{min-height:145px!important;border-radius:18px!important;background:linear-gradient(145deg,rgba(17,31,50,.94),rgba(6,13,24,.92))!important}
.metric:before{width:58px!important;height:58px!important;border-radius:18px!important;font-size:30px!important}
.metric strong{font-size:34px!important}
.metric:hover{box-shadow:0 18px 40px rgba(0,0,0,.25);transform:translateY(-5px)}
.result-wrap{border-radius:18px!important}
.result-head{padding:14px 16px!important;background:linear-gradient(90deg,rgba(104,220,255,.045),rgba(169,139,255,.04))!important}
.result{min-height:180px!important}
.side-card{padding:18px!important}
.status-card{padding:15px!important;border-radius:17px!important}
.map-item{min-height:62px!important;display:flex;flex-direction:column;justify-content:center}
.cert{position:relative;overflow:hidden}.cert:after{content:"✓";position:absolute;right:12px;top:8px;font-size:42px;color:rgba(92,224,178,.08);font-weight:900}
/* visual coffee shelf */
.coffee-shelf{display:flex;align-items:center;gap:10px;margin-top:14px;padding:10px 14px;border:1px solid rgba(104,220,255,.1);border-radius:15px;background:linear-gradient(90deg,rgba(104,220,255,.035),rgba(255,120,141,.025));overflow:hidden}
.coffee-shelf span{font-size:22px;animation:shelfFloat 3s ease-in-out infinite}.coffee-shelf span:nth-child(2){animation-delay:-.7s}.coffee-shelf span:nth-child(3){animation-delay:-1.4s}.coffee-shelf span:nth-child(4){animation-delay:-2.1s}.coffee-shelf b{font:700 10px 'DM Mono';letter-spacing:1px;color:#71859d}
@keyframes shelfFloat{50%{transform:translateY(-4px) rotate(-3deg)}}
/* semantic result glow */
.result-wrap:has(.result:not(:empty)){animation:resultReady .7s var(--ease)}
@keyframes resultReady{from{transform:translateY(7px);opacity:.72}to{transform:none;opacity:1}}
@media(max-width:1080px){.hero-visual{opacity:.48;right:-40px}.round{min-height:94px!important}.field{min-height:130px!important}}
@media(max-width:760px){.hero{min-height:390px!important;padding:32px 25px!important}.hero-visual{position:absolute;width:100%;right:-28%;top:130px;opacity:.2}.round{min-height:90px!important}.metric{min-height:130px!important}.metric strong{font-size:29px!important}}
</style>'''

VISUAL_PATCH = r'''<script>
(function(){
  const iconMap={'Q hot':'☕','Q cold':'🧊','Objective':'💰','Precio':'💵','Margen':'📈','Demanda':'👥','Llegadas':'🚶','Inventario':'📦','Servicio':'🧑‍🍳','Tasa':'⚡','Costo':'💳','Capacidad':'🏪','Probabilidad':'🎯','Markup':'🏷️'};
  const paintIcons=()=>{document.querySelectorAll('.metric').forEach((el,i)=>{const text=el.innerText||'';let icon=i===0?'☕':i===1?'🧊':'💰';for(const k in iconMap)if(text.toLowerCase().includes(k.toLowerCase()))icon=iconMap[k];el.style.setProperty('--semantic-icon',JSON.stringify(icon));});document.querySelectorAll('.field label').forEach(label=>{const t=label.textContent||'';for(const k in iconMap)if(t.toLowerCase().includes(k.toLowerCase())){label.dataset.icon=iconMap[k];break;}});};
  const inject=()=>{if(document.getElementById('gurobean-visual-patch'))return;const s=document.createElement('style');s.id='gurobean-visual-patch';s.textContent='.metric:before{content:var(--semantic-icon,"☕")!important}.field label:before{content:attr(data-icon)!important}';document.head.appendChild(s);paintIcons();};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',inject);else inject();new MutationObserver(paintIcons).observe(document.body,{subtree:true,childList:true});window.gurobeanVisualRefresh=paintIcons;
  const addShelf=()=>{if(document.querySelector('.coffee-shelf'))return;const anchor=document.querySelector('.fields');if(!anchor||!anchor.parentElement)return;const shelf=document.createElement('div');shelf.className='coffee-shelf';shelf.innerHTML='<span>☕</span><span>🥐</span><span>🫘</span><span>🧊</span><b>COFFEE DECISION LAB · LIVE SIGNALS</b>';anchor.parentElement.insertBefore(shelf,anchor.nextSibling);};
  const animateMetrics=()=>document.querySelectorAll('.metric strong').forEach(el=>{if(el.dataset.gurobeanAnimated)return;const raw=el.textContent.trim();const m=raw.match(/(-?\d+(?:[.,]\d+)?)/);if(!m)return;el.dataset.gurobeanAnimated='1';const target=parseFloat(m[1].replace(',','.'));if(!Number.isFinite(target))return;const prefix=raw.slice(0,m.index),suffix=raw.slice(m.index+m[0].length);let start=0,t0=performance.now();const tick=t=>{const p=Math.min(1,(t-t0)/650),e=1-Math.pow(1-p,3);el.textContent=prefix+(target*e).toFixed(Math.abs(target)<10?2:1)+suffix;if(p<1)requestAnimationFrame(tick)};requestAnimationFrame(tick);});
  const refresh=()=>{paintIcons();addShelf();animateMetrics()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh);else refresh();
  new MutationObserver(refresh).observe(document.body,{subtree:true,childList:true});
})();
</script>'''

PATCH = r'''<script>
(function(){const originalSolve=window.solve;window.solve=async function(){try{return await originalSolve();}catch(e){const n=document.getElementById('note');if(n)n.textContent='Error ejecutando el motor: '+e.message;throw e;}};window.compare=async function(){const n=document.getElementById('note');if(n)n.textContent='La comparación formal Gurobi ↔ SciPy requiere el entorno local con licencia Gurobi. Esta consola pública ejecuta la referencia SciPy y la simulación R5–R8.';};})();
</script>'''

@app.get("/")
def ui() -> HTMLResponse:
    if not HTML_PATH.is_file():
        return HTMLResponse("<h1>Gurobean UI unavailable</h1>", status_code=500)
    html = HTML_PATH.read_text(encoding="utf-8")
    replacements = {
        "Modo juego R1–R8": "Modo Juego · R1 → R8", "Modo juego R1-R8": "Modo Juego · R1 → R8",
        "Modo personalizado": "Modo Personalizado", "Modo Personalizado": "Modo Personalizado",
        "🎥 Capturar juego real": "🎥 Capturar juego en vivo", "Capturar juego real": "Capturar juego en vivo",
        "(r>=5?'simulation':'gurobi')": "(r>=5?'simulation':'scipy')", "arrival_reference_rate:36": "arrival_reference_rate:Math.min(36,v('lambda_total',60))",
        '<option value="gurobi">Gurobi · PWL</option>': '<option value="scipy">SciPy · referencia pública</option>',
        "fetch('/solve'": "fetch('/api/solve'", 'fetch("/solve"': 'fetch("/api/solve"', "fetch('/health'": "fetch('/api/health'", 'fetch("/health"': 'fetch("/api/health"',
        "fetch('/evaluate'": "fetch('/api/evaluate'", 'fetch("/evaluate"': 'fetch("/api/evaluate"', "fetch('/ai/ask'": "fetch('/api/ai/ask'", 'fetch("/ai/ask"': 'fetch("/api/ai/ask"',
    }
    for old, new in replacements.items(): html = html.replace(old, new)
    html = html.replace('</head>', READABLE_UI + PREMIUM_VISUAL + '</head>', 1)
    html = html.replace('</body>', '<!-- READABLE UI + PREMIUM COFFEE COCKPIT -->' + VISUAL_PATCH + PATCH + '</body>')
    return HTMLResponse(html, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0", "CDN-Cache-Control":"no-store", "Vercel-CDN-Cache-Control":"no-store"})
