from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"
app = FastAPI()

READABLE_UI = r'''<style id="gurobean-readable-ui">
:root{font-size:16px}
body{font-size:16px!important}
.brand h1{font-size:18px!important}.brand p{font-size:10px!important}
.pill{font-size:12px!important;padding:10px 13px!important}
.btn{font-size:12px!important;padding:11px 14px!important}
.mode{font-size:12px!important;padding:10px 14px!important}
.eyebrow,.kicker{font-size:11px!important}
.hero p{font-size:14px!important;line-height:1.7!important}
.chip{font-size:11px!important;padding:8px 12px!important}
.round{font-size:12px!important;padding:13px 6px!important}.round small{font-size:9px!important}
.title{font-size:21px!important}.desc{font-size:12px!important}.badge{font-size:10px!important}
.field label{font-size:11px!important}.field input,.field select,.chat input{font-size:13px!important;padding:11px!important}.field small{font-size:9px!important}
.note{font-size:11px!important}.result-head span{font-size:10px!important}.result{font-size:11px!important;line-height:1.7!important}
.metric small{font-size:9px!important}.metric strong{font-size:24px!important}.metric em{font-size:9px!important}
.side-title h3{font-size:14px!important}.side-title span{font-size:10px!important}.status-line{font-size:12px!important}
.status-card p,.side-section h4{font-size:10px!important}.map-item{font-size:10px!important;padding:10px 4px!important}.map-item span{font-size:8px!important}
.event{font-size:10px!important}.cert b{font-size:12px!important}.cert span{font-size:9px!important}.answer{font-size:10px!important}
.custom-panel label{font-size:10px!important}.custom-panel select{font-size:11px!important}.footer{font-size:9px!important}.toast{font-size:11px!important}
@media(max-width:760px){.hero p{font-size:13px!important}.hero h2{font-size:38px!important}}
</style>'''

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
    html = html.replace('</body>', '<!-- READABLE UI: enlarged typography for desktop accessibility -->' + PATCH + '</body>')
    return HTMLResponse(html)
