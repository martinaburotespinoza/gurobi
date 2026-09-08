from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"
app = FastAPI()

PATCH = r'''<style>
#liveCapture{position:fixed;right:18px;bottom:18px;z-index:9999;text-decoration:none;background:#173b68;color:#fff;border:1px solid #2c5785;border-radius:999px;padding:11px 15px;font:800 11px system-ui,-apple-system,"Segoe UI",sans-serif;box-shadow:0 10px 30px rgba(23,59,104,.22)}#liveCapture:hover{transform:translateY(-1px)}
</style><a id="liveCapture" href="/capture">🎥 Capturar juego en vivo</a><script>
(function(){
  const status=document.getElementById('status');
  const note=document.getElementById('note');
  function setStatus(kind,text){
    if(!status)return;
    const dot=status.querySelector('.dot');
    if(dot)dot.className='dot '+(kind||'');
    status.lastChild.textContent=' '+text;
  }
  async function health(){
    const paths=['/api/health','/health'];
    let last='';
    for(const path of paths){
      try{
        const r=await fetch(path,{cache:'no-store',headers:{Accept:'application/json'}});
        if(!r.ok)throw new Error('HTTP '+r.status);
        const data=await r.json();
        if(data&&data.status==='ok'){
          setStatus('ok','Motor conectado');
          return true;
        }
        last='Respuesta inválida';
      }catch(e){last=e.message||String(e)}
    }
    setStatus('bad','Motor desconectado');
    if(note)note.textContent='No se pudo conectar con el motor. Actualiza la página para reintentar.';
    return false;
  }
  window.gurobeanHealth=health;
  window.addEventListener('error',function(e){
    if(note&&e&&e.message)note.textContent='Error de interfaz: '+e.message;
  });
  health();
  setInterval(health,30000);
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
