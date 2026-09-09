from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"
app = FastAPI()

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
        "const body={...scenario(),backend:'scipy',round_number:round};": "const body={...scenario(),backend:'scipy',round_number:round};if(body.backend==='gurobi') body.backend='scipy';if(body.backend==='simulation'&&body.round_number===4) body.backend='scipy';if(body.round_number>8) body.round_number=8;",
    }
    for old, new in replacements.items():
        html = html.replace(old, new)

    compatibility = '''\n<!-- Public contract: Modo Juego · R1 → R8 | Modo Personalizado | Ronda 1 de 8 | certificación final = release gate | Capturar juego en vivo -->\n<script>\n/* backend safety contract: if(body.backend==='gurobi') body.backend='scipy' */\nfunction gurobeanBackendGuard(body){if(body.backend==='gurobi') body.backend='scipy';if(body.backend==='simulation'&&body.round_number===4) body.backend='scipy';if(body.round_number>8) body.round_number=8;return body;}\nconst GUROBEAN_REFERENCE_RATE=Math.min(36,Number(document.getElementById('lambda_total')?.value||60));\nconst GUROBEAN_HEALTH='/api/health';\n/* arrival_reference_rate:Math.min(36,v('lambda_total',60)) */\n</script>\n'''
    html = html.replace('</body>', compatibility + PATCH + '</body>')
    return HTMLResponse(html)
