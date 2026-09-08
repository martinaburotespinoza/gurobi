from pathlib import Path
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"

# Browser-safe patch: the public Vercel runtime does not provide the licensed
# gurobipy environment used by the local R1-R4 certification gate. The public
# console therefore uses the independent SciPy reference backend for execution
# and keeps Gurobi as a local certification backend.
PATCH = r'''<script>
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
      if(n) n.textContent='Error ejecutando el motor: '+e.message;
      throw e;
    }
  };
  const originalCompare=window.compare;
  window.compare=async function(){
    const n=document.getElementById('note');
    if(window.mode==='custom'||window.round>4){
      if(n) n.textContent='La comparación formal Gurobi ↔ SciPy está disponible para R1–R4 en el entorno certificado local.';
      return;
    }
    if(n) n.textContent='La consola pública ejecuta la referencia SciPy. La certificación Gurobi se realiza con licencia local.';
    return originalCompare();
  };
})();
</script>'''

def handler(request):
    if not HTML_PATH.is_file():
        return HTMLResponse('<h1>Gurobean UI unavailable</h1>', status_code=500)
    html = HTML_PATH.read_text(encoding='utf-8')
    html = html.replace("(r>=5?'simulation':'gurobi')", "(r>=5?'simulation':'scipy')")
    html = html.replace("['gurobi',", "['scipy',")
    html = html.replace('</body>', PATCH + '</body>')
    return HTMLResponse(html)

# Vercel Python function entrypoint.
app = handler
