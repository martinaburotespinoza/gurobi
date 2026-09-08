from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"
app = FastAPI()

PATCH = r'''<style>
#liveCapture{position:fixed;right:18px;bottom:18px;z-index:9999;text-decoration:none;background:#173b68;color:#fff;border:1px solid #2c5785;border-radius:999px;padding:11px 15px;font:800 11px system-ui,-apple-system,"Segoe UI",sans-serif;box-shadow:0 10px 30px rgba(23,59,104,.22)}#liveCapture:hover{transform:translateY(-1px)}
</style><a id="liveCapture" href="/capture">🎥 Capturar juego en vivo</a><script>
(function(){
  const originalSolve=window.solve;
  window.solve=async function(){
    try{
      if(window.mode==='custom' && document.getElementById('custom_backend')){
        const b=document.getElementById('custom_backend');
        if(b.value==='gurobi') b.value='scipy';
      }
      return await originalSolve();
    }catch(e){
      const n=document.getElementById('note');
      if(n)n.textContent='Error ejecutando el motor: '+e.message;
      throw e;
    }
  };
  const originalCompare=window.compare;
  window.compare=async function(){
    const n=document.getElementById('note');
    if(window.mode==='custom'||window.round>4){
      if(n)n.textContent='La comparación formal Gurobi ↔ SciPy está disponible para R1–R4 en el entorno certificado local.';
      return;
    }
    if(n)n.textContent='La consola pública ejecuta la referencia SciPy. La certificación Gurobi se realiza con licencia local.';
    return originalCompare();
  };
})();
</script>'''

@app.get("/")
def ui() -> HTMLResponse:
    if not HTML_PATH.is_file():
        return HTMLResponse("<h1>Gurobean UI unavailable</h1>", status_code=500)
    html = HTML_PATH.read_text(encoding="utf-8")
    html = html.replace("(r>=5?'simulation':'gurobi')", "(r>=5?'simulation':'scipy')")
    html = html.replace("arrival_reference_rate:36", "arrival_reference_rate:Math.min(36,v('lambda_total',60))")
    html = html.replace('<option value="gurobi">Gurobi · PWL</option>', '<option value="scipy">SciPy · referencia</option>')
    html = html.replace('</body>', PATCH + '</body>')
    return HTMLResponse(html)
