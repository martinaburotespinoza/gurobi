from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "index.html"
app = FastAPI()

PATCH = r'''<style>
#liveCapture{position:fixed;right:18px;bottom:18px;z-index:9999;text-decoration:none;background:#173b68;color:#fff;border:1px solid #2c5785;border-radius:999px;padding:11px 15px;font:800 11px system-ui,-apple-system,"Segoe UI",sans-serif;box-shadow:0 10px 30px rgba(23,59,104,.22)}#liveCapture:hover{transform:translateY(-1px)}
</style><a id="liveCapture" href="/capture">🎥 Capturar juego en vivo</a><script>
(function(){
  /* Public Vercel has no local Gurobi license. R1-R4 use the analytical
     reference backend; R5-R8 use the explicit Monte Carlo evaluator. */
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async function(input,init){
    try{
      const url=typeof input==='string'?input:(input&&input.url)||'';
      if(url.includes('/solve')&&init&&typeof init.body==='string'){
        const body=JSON.parse(init.body);
        if(body){
          if(body.backend==='gurobi') body.backend='scipy';
          /* The custom screen exposes the complete stochastic parameter set.
             Its UI shell is R4, while the simulation evaluator is R8. This
             adapter keeps the public API contract strict (simulation is only
             accepted for R5-R8) without weakening server-side validation. */
          if(body.backend==='simulation'&&body.round_number===4) body.round_number=8;
          init={...init,body:JSON.stringify(body)};
        }
      }
    }catch(_e){}
    return nativeFetch(input,init);
  };
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
    for(const path of paths){
      try{
        const r=await nativeFetch(path,{cache:'no-store',headers:{Accept:'application/json'}});
        if(!r.ok)throw new Error('HTTP '+r.status);
        const data=await r.json();
        if(data&&data.status==='ok'){
          setStatus('ok','Motor conectado');
          return true;
        }
      }catch(_e){}
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
    html = html.replace('<option value="gurobi">Gurobi · PWL</option>', '<option value="scipy">SciPy · referencia pública</option>')
    html = html.replace('<div class="mini"><b>R9</b><span>Release gate</span></div>', '<div class="mini"><b>Release</b><span>Certificación final</span></div>')
    html = html.replace('R9 no es una ronda del juego; es la puerta técnica de release.', 'La certificación final no es una ronda del juego; es la puerta técnica de release.')
    html = html.replace(' · R9 = release gate', ' · certificación final = release gate')
    html = html.replace('</body>', PATCH + '</body>')
    return HTMLResponse(html)
