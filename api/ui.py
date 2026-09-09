from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"
app = FastAPI()

READABLE_UI = r'''<style id="gurobean-readable-ui">
:root{font-size:18px!important}
body{font-size:18px!important}
.app{width:min(1680px,100%)!important;padding:24px 28px 52px!important}
.topbar{height:78px!important;margin-bottom:18px!important}
.brand{gap:16px!important}.brand h1{font-size:23px!important;letter-spacing:.4px}.brand p{font-size:12px!important;margin-top:5px!important}
.pill{font-size:14px!important;padding:12px 16px!important}.btn{font-size:14px!important;padding:13px 17px!important;border-radius:13px!important}
.mode{font-size:14px!important;padding:13px 17px!important}.eyebrow,.kicker{font-size:13px!important}
.hero{min-height:390px!important;padding:52px 56px!important;border-radius:34px!important}.hero-copy{max-width:900px!important}.hero h2{font-size:clamp(42px,5vw,72px)!important;line-height:.98!important;letter-spacing:-3px!important}.hero p{font-size:17px!important;line-height:1.8!important;max-width:820px!important}.chip{font-size:13px!important;padding:10px 14px!important}
.toolbar{min-height:66px!important;margin:18px 0!important}.rounds{gap:10px!important}.round{font-size:16px!important;padding:18px 8px!important;min-height:118px!important;border-radius:17px!important}.round small{font-size:11px!important;margin-top:6px!important}.round:after{font-size:34px!important}
.shell{grid-template-columns:minmax(0,1fr) 380px!important;gap:18px!important}.main-card{padding:25px!important;border-radius:26px!important}.side-card{padding:22px!important;border-radius:26px!important}
.title{font-size:30px!important;letter-spacing:-.7px!important}.desc{font-size:15px!important;line-height:1.65!important}.badge{font-size:12px!important;padding:9px 11px!important}
.fields{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))!important;gap:12px!important;margin-top:19px!important}.field{min-height:156px!important;padding:18px!important;border-radius:18px!important}.field label{font-size:14px!important;margin-bottom:9px!important}.field input,.field select,.chat input{font-size:17px!important;padding:14px!important;min-height:54px!important;border-radius:13px!important}.field small{font-size:11px!important;margin-top:7px!important}
.actions{gap:9px!important;margin-top:18px!important}.solve-btn{font-size:17px!important;padding:17px 23px!important;min-width:220px!important}
.note{font-size:13px!important;padding:13px 15px!important}.result-wrap{border-radius:20px!important}.result-head{padding:16px 18px!important}.result-head span{font-size:12px!important}.result{font-size:13px!important;line-height:1.85!important;min-height:210px!important;padding:18px!important}
.metrics{gap:10px!important;margin-top:13px!important}.metric{min-height:164px!important;padding:21px!important;border-radius:20px!important;grid-template-columns:64px 1fr!important;column-gap:14px!important}.metric:before{width:64px!important;height:64px!important;border-radius:20px!important;font-size:34px!important}.metric small{font-size:11px!important}.metric strong{font-size:38px!important;letter-spacing:-1px!important}.metric em{font-size:11px!important}
.side-title h3{font-size:17px!important}.side-title span{font-size:12px!important}.status-card{padding:18px!important;border-radius:19px!important}.status-line{font-size:14px!important}.status-card p,.side-section h4{font-size:12px!important;line-height:1.55!important}.map-item{font-size:12px!important;padding:13px 7px!important;min-height:70px!important}.map-item span{font-size:10px!important}.event{font-size:12px!important;padding:10px 0!important}.cert b{font-size:14px!important}.cert span{font-size:11px!important}.answer{font-size:12px!important}
.custom-panel label{font-size:12px!important}.custom-panel select{font-size:14px!important}.footer{font-size:11px!important}.toast{font-size:13px!important}
.logo{font-size:0!important;width:66px!important;height:66px!important;border-radius:19px!important;position:relative!important;overflow:visible!important;background:linear-gradient(145deg,#172f4b,#07101e)!important;border:1px solid rgba(104,220,255,.42)!important;box-shadow:0 0 42px rgba(104,220,255,.16)!important;display:grid!important;place-items:center!important}
.logo svg{width:50px!important;height:50px!important;display:block!important;filter:drop-shadow(0 6px 14px rgba(104,220,255,.28))}
.round{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:6px!important}.round:after{font-size:34px!important;line-height:1!important;content:'☕';opacity:1;order:-1;filter:drop-shadow(0 4px 10px rgba(104,220,255,.28))}
.round[data-nav-round="1"]:after{content:'☕'}.round[data-nav-round="2"]:after{content:'🧊'}.round[data-nav-round="3"]:after{content:'📈'}.round[data-nav-round="4"]:after{content:'⚙️'}.round[data-nav-round="5"]:after{content:'👥'}.round[data-nav-round="6"]:after{content:'📦'}.round[data-nav-round="7"]:after{content:'💳'}.round[data-nav-round="8"]:after{content:'🏆'}
.field{background:linear-gradient(145deg,rgba(255,255,255,.045),rgba(104,220,255,.018))!important}.field label:before{content:'◉';color:var(--cyan);margin-right:8px;font-size:13px}
.metric{display:grid!important;grid-template-rows:auto auto auto!important}.metric:before{grid-row:1/4;display:grid;place-items:center;background:rgba(104,220,255,.09);border:1px solid rgba(104,220,255,.18);content:'☕';animation:metricFloat 3s ease-in-out infinite}.metric:nth-child(2):before{content:'❄️'}.metric:nth-child(3):before{content:'💰'}.metric small,.metric strong,.metric em{grid-column:2}@keyframes metricFloat{50%{transform:translateY(-4px) rotate(-2deg)}}
.result-head:before{content:'🧠';font-size:23px;margin-right:9px}.result-head{justify-content:flex-start}.status-line:before{content:'⚡';font-size:21px}.side-section h4:before{margin-right:7px}.side-section:nth-of-type(1) h4:before{content:'📡'}.side-section:nth-of-type(2) h4:before{content:'🗺️'}.side-section:nth-of-type(3) h4:before{content:'✨'}
.solve-btn:before{content:'☕ ';font-size:21px}.btn.primary:before{content:'✦ ';font-size:16px}.hero:after{content:'☕';position:absolute;right:31%;bottom:-34px;font-size:190px;opacity:.055;filter:blur(.2px);transform:rotate(-12deg);pointer-events:none;animation:heroCup 7s ease-in-out infinite}@keyframes heroCup{50%{transform:rotate(-7deg) translateY(-10px)}}
</style>'''

PREMIUM_VISUAL = r'''<style id="gurobean-premium-visual">
.app{position:relative}.app:before{content:"";position:fixed;inset:10% 4% auto;max-width:1600px;height:1px;margin:auto;background:linear-gradient(90deg,transparent,rgba(104,220,255,.18),transparent);pointer-events:none}
.hero{min-height:410px!important;border-radius:36px!important;background:linear-gradient(135deg,rgba(17,38,63,.97),rgba(6,13,25,.9))!important}.hero-copy{max-width:900px!important}.hero h2{font-weight:800!important;text-shadow:0 10px 45px rgba(0,0,0,.28)}.hero-visual{filter:drop-shadow(0 24px 55px rgba(47,128,255,.2));transform:scale(1.08);transform-origin:center right}
.toolbar{min-height:68px}.main-card{padding:26px!important}.rounds{gap:10px!important}.round{min-height:122px!important;border-radius:18px!important;background:linear-gradient(180deg,rgba(13,28,48,.94),rgba(5,12,22,.82))!important}.round.active{transform:translateY(-3px);box-shadow:0 22px 45px rgba(60,106,240,.25)!important}.fields{gap:13px!important}.field{min-height:162px!important;border-radius:19px!important;position:relative;overflow:hidden}.field:after{content:"";position:absolute;right:-22px;bottom:-32px;width:110px;height:110px;border-radius:50%;background:radial-gradient(circle,rgba(104,220,255,.1),transparent 68%);pointer-events:none}.field input,.field select,.chat input{min-height:56px!important;background:rgba(2,8,16,.88)!important}.metric{min-height:172px!important;border-radius:20px!important;background:linear-gradient(145deg,rgba(18,34,54,.97),rgba(5,13,24,.94))!important}.metric:before{width:66px!important;height:66px!important;border-radius:21px!important;font-size:35px!important}.metric strong{font-size:40px!important}.metric:hover{box-shadow:0 22px 45px rgba(0,0,0,.28);transform:translateY(-6px)}.result-wrap{border-radius:21px!important}.result-head{padding:16px 18px!important;background:linear-gradient(90deg,rgba(104,220,255,.055),rgba(169,139,255,.055))!important}.result{min-height:220px!important}.side-card{padding:22px!important}.status-card{padding:19px!important;border-radius:20px!important}.map-item{min-height:74px!important;display:flex;flex-direction:column;justify-content:center}.cert{position:relative;overflow:hidden}.cert:after{content:"✓";position:absolute;right:12px;top:7px;font-size:48px;color:rgba(92,224,178,.08);font-weight:900}
.coffee-shelf{display:flex;align-items:center;gap:13px;margin-top:16px;padding:13px 17px;border:1px solid rgba(104,220,255,.14);border-radius:17px;background:linear-gradient(90deg,rgba(104,220,255,.05),rgba(255,120,141,.035));overflow:hidden;box-shadow:inset 0 1px rgba(255,255,255,.03)}.coffee-shelf span{font-size:28px;animation:shelfFloat 3s ease-in-out infinite}.coffee-shelf span:nth-child(2){animation-delay:-.7s}.coffee-shelf span:nth-child(3){animation-delay:-1.4s}.coffee-shelf span:nth-child(4){animation-delay:-2.1s}.coffee-shelf b{font:700 12px 'DM Mono';letter-spacing:1px;color:#8297ae}@keyframes shelfFloat{50%{transform:translateY(-5px) rotate(-3deg)}}
@media(max-width:1080px){.hero-visual{opacity:.5;right:-55px}.round{min-height:104px!important}.field{min-height:145px!important}.shell{grid-template-columns:minmax(0,1fr) 330px!important}}@media(max-width:760px){.app{padding:16px!important}.hero{min-height:430px!important;padding:34px 27px!important}.hero-visual{position:absolute;width:105%;right:-35%;top:145px;opacity:.22;transform:none}.round{min-height:94px!important}.metric{min-height:145px!important}.metric strong{font-size:31px!important}}
</style>'''

VISUAL_PATCH = r'''<script>
(function(){
  const iconMap={'Q hot':'☕','Q cold':'🧊','Objective':'💰','Precio':'💵','Margen':'📈','Demanda':'👥','Llegadas':'🚶','Inventario':'📦','Servicio':'🧑‍🍳','Tasa':'⚡','Costo':'💳','Capacidad':'🏪','Probabilidad':'🎯','Markup':'🏷️'};
  const brandSvg='<svg viewBox="0 0 64 64" aria-label="Gurobean logo" role="img"><defs><linearGradient id="gbg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#68dcff"/><stop offset="1" stop-color="#a98bff"/></linearGradient></defs><path d="M16 24h30v18c0 8-6 13-15 13S16 50 16 42V24Z" fill="none" stroke="url(#gbg)" stroke-width="4"/><path d="M46 29h5c7 0 9 11 1 14h-6" fill="none" stroke="#68dcff" stroke-width="4" stroke-linecap="round"/><path d="M23 18c-2-5 5-6 3-12M34 18c-2-5 5-6 3-12" fill="none" stroke="#f2f7ff" stroke-opacity=".65" stroke-width="3" stroke-linecap="round"/><path d="M22 35c5 3 11 3 18 0" fill="none" stroke="#a98bff" stroke-width="3" stroke-linecap="round"/><circle cx="43" cy="45" r="5" fill="#ff788d" opacity=".9"/></svg>';
  const paintIcons=()=>{document.querySelectorAll('.metric').forEach((el,i)=>{const text=el.innerText||'';let icon=i===0?'☕':i===1?'🧊':'💰';for(const k in iconMap)if(text.toLowerCase().includes(k.toLowerCase()))icon=iconMap[k];el.style.setProperty('--semantic-icon',JSON.stringify(icon));});document.querySelectorAll('.field label').forEach(label=>{const t=label.textContent||'';for(const k in iconMap)if(t.toLowerCase().includes(k.toLowerCase())){label.dataset.icon=iconMap[k];break;}});};
  const inject=()=>{if(document.getElementById('gurobean-visual-patch'))return;const s=document.createElement('style');s.id='gurobean-visual-patch';s.textContent='.metric:before{content:var(--semantic-icon,"☕")!important}.field label:before{content:attr(data-icon)!important}';document.head.appendChild(s);const logo=document.querySelector('.logo');if(logo)logo.innerHTML=brandSvg;paintIcons();};
  const addShelf=()=>{if(document.querySelector('.coffee-shelf'))return;const anchor=document.querySelector('.fields');if(!anchor||!anchor.parentElement)return;const shelf=document.createElement('div');shelf.className='coffee-shelf';shelf.innerHTML='<span>☕</span><span>🥐</span><span>🫘</span><span>🧊</span><b>GUROBEAN COFFEE DECISION LAB · LIVE</b>';anchor.parentElement.insertBefore(shelf,anchor.nextSibling);};
  const animateMetrics=()=>document.querySelectorAll('.metric strong').forEach(el=>{if(el.dataset.gurobeanAnimated)return;const raw=el.textContent.trim();const m=raw.match(/(-?\d+(?:[.,]\d+)?)/);if(!m)return;el.dataset.gurobeanAnimated='1';const target=parseFloat(m[1].replace(',','.'));if(!Number.isFinite(target))return;const prefix=raw.slice(0,m.index),suffix=raw.slice(m.index+m[0].length);const t0=performance.now();const tick=t=>{const p=Math.min(1,(t-t0)/650),e=1-Math.pow(1-p,3);el.textContent=prefix+(target*e).toFixed(Math.abs(target)<10?2:1)+suffix;if(p<1)requestAnimationFrame(tick)};requestAnimationFrame(tick);});
  const refresh=()=>{paintIcons();addShelf();animateMetrics();const logo=document.querySelector('.logo');if(logo&&!logo.querySelector('svg'))logo.innerHTML=brandSvg};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{inject();refresh()});else{inject();refresh()}
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
