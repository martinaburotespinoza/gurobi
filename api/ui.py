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
.round{font-size:13px!important;padding:15px 7px!important}.round small{font-size:10px!important}
.title{font-size:23px!important}.desc{font-size:13px!important}.badge{font-size:11px!important}
.field label{font-size:12px!important}.field input,.field select,.chat input{font-size:14px!important;padding:12px!important}.field small{font-size:10px!important}
.note{font-size:12px!important}.result-head span{font-size:11px!important}.result{font-size:12px!important;line-height:1.75!important}
.metric small{font-size:10px!important}.metric strong{font-size:28px!important}.metric em{font-size:10px!important}
.side-title h3{font-size:15px!important}.side-title span{font-size:11px!important}.status-line{font-size:13px!important}
.status-card p,.side-section h4{font-size:11px!important}.map-item{font-size:11px!important;padding:11px 5px!important}.map-item span{font-size:9px!important}
.event{font-size:11px!important}.cert b{font-size:13px!important}.cert span{font-size:10px!important}.answer{font-size:11px!important}
.custom-panel label{font-size:11px!important}.custom-panel select{font-size:12px!important}.footer{font-size:10px!important}.toast{font-size:12px!important}
/* Visual cockpit enhancement: larger modules, illustrated semantic icons and coffee motion */
.logo{font-size:0!important;width:54px!important;height:54px!important;border-radius:16px!important;position:relative;overflow:hidden!important;background:linear-gradient(145deg,#162f4b,#07101e)!important}
.logo:after{content:'☕';font-size:28px;filter:drop-shadow(0 4px 10px rgba(104,220,255,.3));animation:coffeePulse 2.8s ease-in-out infinite}
@keyframes coffeePulse{0%,100%{transform:translateY(1px) scale(1)}50%{transform:translateY(-3px) scale(1.08)}}
.round{min-height:76px!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:3px!important}
.round:after{font-size:20px!important;line-height:1!important;content:'☕';opacity:.8;order:-1}
.round[data-nav-round="1"]:after{content:'☕'}.round[data-nav-round="2"]:after{content:'🧊'}.round[data-nav-round="3"]:after{content:'📈'}.round[data-nav-round="4"]:after{content:'⚙️'}.round[data-nav-round="5"]:after{content:'👥'}.round[data-nav-round="6"]:after{content:'📦'}.round[data-nav-round="7"]:after{content:'💳'}.round[data-nav-round="8"]:after{content:'🏆'}
.field{min-height:112px!important;padding:14px!important}.field label:before{content:'◉';color:var(--cyan);margin-right:7px;font-size:12px}
.metric{min-height:112px!important;padding:17px!important;display:grid!important;grid-template-columns:42px 1fr!important;grid-template-rows:auto auto auto!important;column-gap:10px!important}
.metric:before{grid-row:1/4;display:grid;place-items:center;width:42px;height:42px;border-radius:14px;background:rgba(104,220,255,.09);border:1px solid rgba(104,220,255,.16);font-size:23px;content:'☕';animation:metricFloat 3s ease-in-out infinite}
.metric:nth-child(2):before{content:'❄️'}.metric:nth-child(3):before{content:'💰'}
.metric small,.metric strong,.metric em{grid-column:2}
@keyframes metricFloat{50%{transform:translateY(-3px) rotate(-2deg)}}
.result-wrap{box-shadow:inset 0 0 0 1px rgba(104,220,255,.025),0 18px 50px rgba(0,0,0,.2)}
.result-head:before{content:'🧠';font-size:17px;margin-right:7px}.result-head{justify-content:flex-start}.result-head span{margin-left:0}
.status-line:before{content:'⚡';font-size:17px}.side-section h4:before{margin-right:6px}.side-section:nth-of-type(1) h4:before{content:'📡'}.side-section:nth-of-type(2) h4:before{content:'🗺️'}.side-section:nth-of-type(3) h4:before{content:'✨'}
.event i{width:9px;height:9px;flex-basis:9px}.event i:after{content:''}
.solve-btn{font-size:14px!important;padding:14px 18px!important;box-shadow:0 16px 38px rgba(65,119,255,.3)!important}
.solve-btn:before{content:'☕ ';font-size:17px}
.btn.primary:before{content:'✦ ';font-size:14px}
.hero:after{content:'☕';position:absolute;right:34%;bottom:-30px;font-size:130px;opacity:.035;filter:blur(.3px);transform:rotate(-12deg);pointer-events:none;animation:heroCup 7s ease-in-out infinite}
@keyframes heroCup{50%{transform:rotate(-7deg) translateY(-8px)}}
@media(max-width:760px){.hero p{font-size:14px!important}.hero h2{font-size:40px!important}.round{min-height:70px!important}.metric strong{font-size:25px!important}}
@media(max-width:430px){.brand h1{font-size:18px!important}.hero h2{font-size:34px!important}.field input,.field select{font-size:15px!important}.btn,.mode{font-size:13px!important}}
</style>'''

VISUAL_PATCH = r'''<script>
(function(){
  const iconMap={
    'Q hot':'☕','Q cold':'🧊','Objective':'💰','Precio':'💵','Margen':'📈','Demanda':'👥','Llegadas':'🚶','Inventario':'📦','Servicio':'🧑‍🍳','Tasa':'⚡','Costo':'💳','Capacidad':'🏪','Probabilidad':'🎯','Markup':'🏷️'
  };
  const paintIcons=()=>{
    document.querySelectorAll('.metric').forEach((el,i)=>{
      const text=el.innerText||'';let icon=i===0?'☕':i===1?'🧊':'💰';
      for(const k in iconMap)if(text.toLowerCase().includes(k.toLowerCase()))icon=iconMap[k];
      el.style.setProperty('--semantic-icon',JSON.stringify(icon));
    });
    document.querySelectorAll('.field label').forEach(label=>{
      const t=label.textContent||'';for(const k in iconMap)if(t.toLowerCase().includes(k.toLowerCase())){label.dataset.icon=iconMap[k];break;}
    });
  };
  const inject=()=>{
    if(document.getElementById('gurobean-visual-patch'))return;
    const s=document.createElement('style');s.id='gurobean-visual-patch';s.textContent='.metric:before{content:var(--semantic-icon,"☕")!important}.field label:before{content:attr(data-icon)!important}';document.head.appendChild(s);paintIcons();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',inject);else inject();
  new MutationObserver(paintIcons).observe(document.body,{subtree:true,childList:true});
  window.gurobeanVisualRefresh=paintIcons;
})();
</script>'''

PATCH = r'''<script>
(function(){
  const originalSolve=window.solve;
  window.solve=async function(){
    try{return await originalSolve();}
    catch(e){
      const n=document.getElementById('note');
      if(n)n.textContent='Error ejecutando el motor: '+e.message;
      throw e;
    }
  };
  window.compare=async function(){
    const n=document.getElementById('note');
    if(n)n.textContent='La comparación formal Gurobi ↔ SciPy requiere el entorno local con licencia Gurobi. Esta consola pública ejecuta la referencia SciPy y la simulación R5–R8.';
  };
})();
</script>'''

@app.get("/")
def ui() -> HTMLResponse:
    if not HTML_PATH.is_file():
        return HTMLResponse("<h1>Gurobean UI unavailable</h1>", status_code=500)
    html = HTML_PATH.read_text(encoding="utf-8")
    replacements = {
        "Modo juego R1–R8": "Modo Juego · R1 → R8",
        "Modo juego R1-R8": "Modo Juego · R1 → R8",
        "Modo personalizado": "Modo Personalizado",
        "Modo Personalizado": "Modo Personalizado",
        "🎥 Capturar juego real": "🎥 Capturar juego en vivo",
        "Capturar juego real": "Capturar juego en vivo",
        "(r>=5?'simulation':'gurobi')": "(r>=5?'simulation':'scipy')",
        "arrival_reference_rate:36": "arrival_reference_rate:Math.min(36,v('lambda_total',60))",
        '<option value="gurobi">Gurobi · PWL</option>': '<option value="scipy">SciPy · referencia pública</option>',
        "fetch('/solve'": "fetch('/api/solve'",
        'fetch("/solve"': 'fetch("/api/solve"',
        "fetch('/health'": "fetch('/api/health'",
        'fetch("/health"': 'fetch("/api/health"',
        "fetch('/evaluate'": "fetch('/api/evaluate'",
        'fetch("/evaluate"': 'fetch("/api/evaluate"',
        "fetch('/ai/ask'": "fetch('/api/ai/ask'",
        'fetch("/ai/ask"': 'fetch("/api/ai/ask"',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    html = html.replace('</head>', READABLE_UI + '</head>', 1)
    html = html.replace('</body>', '<!-- READABLE UI + VISUAL COCKPIT -->' + VISUAL_PATCH + PATCH + '</body>')
    return HTMLResponse(html)
