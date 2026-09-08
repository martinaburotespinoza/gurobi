"""R9 end-to-end certification for the R1-R4 Gurobean pipeline.

Default mode validates the independent reference without pretending that a
missing Gurobi installation is a solver PASS. `--require-gurobi` is the
mandatory release mode: real Gurobi, 20,001 PWL points, regret <= 2e-6 and
feasibility <= 1e-8 are required across all 400 checks.
"""
from __future__ import annotations
import argparse,json,math,random
from dataclasses import asdict,dataclass
from pathlib import Path
import numpy as np
from gurobean.model import Scenario,_feasible,_round_bounds,_round_objective,expected_newsvendor_gradient,solve_gurobi_round
SEED=902026;CASES=100;ROUNDS=(1,2,3,4);REFERENCE_OBJ_TOL=2e-7;STRICT_REGRET_TOL=2e-6;FEAS_TOL=1e-8;R9_PWL_POINTS=20001
@dataclass(frozen=True)
class CaseResult:
 case:int;round_number:int;reference_ok:bool;gurobi_checked:bool;gurobi_ok:bool;q_hot:float;q_cold:float;reference_objective:float;exact_objective:float;objective_error:float;regret:float;q_error:float;feasible:bool;deterministic:bool;error:str|None=None
def _scenario(rng,edge):
 if edge==0:lam,p_hot,p_cold=.05,1.,0.
 elif edge==1:lam,p_hot,p_cold=80.,.35,.65
 elif edge==2:lam,p_hot,p_cold=1e-4,.55,.45
 else:lam=rng.uniform(.05,80.);p_hot=rng.uniform(.05,.95);p_cold=1-p_hot
 rh,rc=rng.uniform(1,8),rng.uniform(1,8);ch,cc=rng.uniform(0,.8*rh),rng.uniform(0,.8*rc);bh,bc=rng.uniform(.05,2),rng.uniform(.05,2);wh,wc=rng.uniform(.1,3),rng.uniform(.1,3);scale=lam*(.55 if edge==1 else rng.uniform(.8,2)) if edge!=2 else .002
 return Scenario(lambda_total=lam,p_hot=p_hot,p_cold=p_cold,revenue_hot=rh,revenue_cold=rc,cost_hot=ch,cost_cold=cc,salvage_hot=0.,salvage_cold=0.,beans_available=scale*rng.uniform(.55,1.25)*max(bh,bc),water_available=scale*rng.uniform(.55,1.25)*max(wh,wc),beans_hot=bh,beans_cold=bc,water_hot=wh,water_cold=wc)
def _objective(sc,r,qh,qc):return _round_objective(sc,r in(2,4),r in(3,4),qh,qc)
def _stationary_q(sc,r,hot):
 from scipy.optimize import brentq
 inc=r in(3,4);cost=(sc.cost_hot if hot else sc.cost_cold) if inc else 0.;lam=sc.lambda_hot if hot else sc.lambda_cold;rev=sc.revenue_hot if hot else sc.revenue_cold;sal=sc.salvage_hot if hot else sc.salvage_cold
 if lam<=0 or expected_newsvendor_gradient(0.,lam,rev,cost,sal)<=0:return 0.
 hi=max(1.,lam)
 while expected_newsvendor_gradient(hi,lam,rev,cost,sal)>0 and hi<1e9:hi*=2
 if hi>=1e9:return float('inf')
 return float(brentq(lambda q:expected_newsvendor_gradient(q,lam,rev,cost,sal),0,hi,xtol=1e-12,rtol=1e-13))
def _ternary(sc,r,a,b):
 lo,hi=0.,1.
 for _ in range(100):
  m1,m2=(2*lo+hi)/3,(lo+2*hi)/3
  if _objective(sc,r,*(a+m1*(b-a)))<_objective(sc,r,*(a+m2*(b-a))):lo=m1
  else:hi=m2
 cand=(lo,(lo+hi)/2,hi,0.,1.);t=max(cand,key=lambda t:_objective(sc,r,*(a+t*(b-a))));x=a+t*(b-a);return float(_objective(sc,r,*x)),x
def _vertices(sc,r):
 hh,ch=_round_bounds(sc,r in(2,4),r in(3,4));lines=[(1,0,0),(0,1,0),(1,0,hh),(0,1,ch),(sc.beans_hot,sc.beans_cold,sc.beans_available),(sc.water_hot,sc.water_cold,sc.water_available)];out=[];tol=1e-9*max(1,hh,ch,abs(sc.beans_available),abs(sc.water_available))
 for i in range(len(lines)):
  for j in range(i+1,len(lines)):
   a,b,c=lines[i];d,e,f=lines[j];det=a*e-d*b
   if abs(det)<=1e-14:continue
   x=(c*e-f*b)/det;y=(a*f-d*c)/det
   if x < -tol or y < -tol or x>hh+tol or y>ch+tol or sc.beans_hot*x+sc.beans_cold*y>sc.beans_available+tol or sc.water_hot*x+sc.water_cold*y>sc.water_available+tol:continue
   v=np.array([max(0,min(hh,x)),max(0,min(ch,y))],float)
   if not any(np.max(abs(v-w))<=1e-9*max(1,np.max(abs(v)),np.max(abs(w))) for w in out):out.append(v)
 if not out:raise RuntimeError('R9 reference polygon has no feasible vertex')
 return out
def _reference(sc,r):
 if r in(1,3):
  hh,_=_round_bounds(sc,False,r in(3,4));q=max(0.,min(hh,_stationary_q(sc,r,True)));return {'Q_hot':float(q),'Q_cold':0.,'objective':float(_objective(sc,r,q,0.))}
 vs=_vertices(sc,r);hh,ch=_round_bounds(sc,True,r==4);s=np.array([min(hh,_stationary_q(sc,r,True)),min(ch,_stationary_q(sc,r,False))]);cand=[]
 if _feasible(*s,sc):cand.append((_objective(sc,r,*s),s))
 cand += [(_objective(sc,r,*v),v) for v in vs];center=np.mean(np.stack(vs),axis=0);ordered=sorted(vs,key=lambda x:math.atan2(float(x[1]-center[1]),float(x[0]-center[0])))
 for i,a in enumerate(ordered):
  b=ordered[(i+1)%len(ordered)]
  if np.max(abs(a-b))>1e-12:cand.append(_ternary(sc,r,a,b))
 val,x=max(cand,key=lambda z:z[0]);return {'Q_hot':float(x[0]),'Q_cold':float(x[1]),'objective':float(val)}
def _strict_feasible(qh,qc,sc):return bool(math.isfinite(qh) and math.isfinite(qc) and qh>=-FEAS_TOL and qc>=-FEAS_TOL and sc.beans_hot*qh+sc.beans_cold*qc<=sc.beans_available+FEAS_TOL and sc.water_hot*qh+sc.water_cold*qc<=sc.water_available+FEAS_TOL)
def certify_case(i,r,sc,require_gurobi,has_gurobi):
 try:
  ref=_reference(sc,r);qh,qc=float(ref['Q_hot']),float(ref['Q_cold']);exact_ref=_objective(sc,r,qh,qc);referr=abs(ref['objective']-exact_ref);ref2=_reference(sc,r);det=abs(qh-ref2['Q_hot'])<=1e-10 and abs(qc-ref2['Q_cold'])<=1e-10 and abs(ref['objective']-ref2['objective'])<=1e-10;hh,ch=_round_bounds(sc,r in(2,4),r in(3,4));refok=bool(_feasible(qh,qc,sc) and -FEAS_TOL<=qh<=hh+FEAS_TOL and -FEAS_TOL<=qc<=ch+FEAS_TOL and referr<=REFERENCE_OBJ_TOL and det)
  if not has_gurobi:
   if require_gurobi:raise RuntimeError('R9 strict mode requires gurobipy and a valid Gurobi environment')
   return CaseResult(i,r,refok,False,True,qh,qc,float(ref['objective']),float(exact_ref),referr,0.,0.,_feasible(qh,qc,sc),det)
  g=solve_gurobi_round(sc,r,pwl_points=R9_PWL_POINTS);gqh,gqc=float(g['Q_hot']),float(g['Q_cold']);exact=_objective(sc,r,gqh,gqc);reg=abs(exact-exact_ref);qerr=max(abs(gqh-qh),abs(gqc-qc));feas=_strict_feasible(gqh,gqc,sc);gok=bool(feas and math.isfinite(exact) and reg<=STRICT_REGRET_TOL)
  return CaseResult(i,r,refok,True,gok,gqh,gqc,float(ref['objective']),float(exact),referr,reg,qerr,feas,det)
 except Exception as exc:return CaseResult(i,r,False,False,False,math.nan,math.nan,math.nan,math.nan,math.inf,math.inf,math.inf,False,False,repr(exc))
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--require-gurobi',action='store_true');args=p.parse_args(argv)
 try:import gurobipy;gv=tuple(gurobipy.gurobi.version());has=True
 except Exception as exc:gv=None;has=False
 if args.require_gurobi and not has:print(f'Gurobi unavailable: {exc}');return 2
 rng=random.Random(SEED);results=[]
 for i in range(CASES):
  sc=_scenario(rng,i%4)
  for r in ROUNDS:results.append(certify_case(i,r,sc,args.require_gurobi,has))
 rf=[x for x in results if not x.reference_ok];gc=[x for x in results if x.gurobi_checked];gf=[x for x in gc if not x.gurobi_ok];worst=max((x.regret for x in gc),default=0.);status='PASS' if len(results)==400 and not rf and ((args.require_gurobi and len(gc)==400 and not gf) or (not args.require_gurobi and not gf)) else 'FAIL';gate='CHECKED' if gc else 'NOT_AVAILABLE_IN_ENVIRONMENT'
 art={'schema':'gurobean.r9.end-to-end.v3','seed':SEED,'cases':CASES,'rounds':list(ROUNDS),'total_cases':len(results),'gurobi_version':gv,'reference_failures':len(rf),'gurobi_cases_checked':len(gc),'gurobi_failures':len(gf),'gurobi_gate':gate,'require_gurobi':bool(args.require_gurobi),'worst_regret':worst,'criteria':{'reference_objective_tol':REFERENCE_OBJ_TOL,'strict_regret_tol':STRICT_REGRET_TOL,'feasibility_tol':FEAS_TOL,'pwl_points':R9_PWL_POINTS},'status':status,'failures':[asdict(x) for x in results if not x.reference_ok or not x.gurobi_ok],'results':[asdict(x) for x in results]};Path('r9_end_to_end.json').write_text(json.dumps(art,indent=2),encoding='utf-8')
 print('=== GUROBEAN R9 END-TO-END ===');print(f'CASES: {CASES} x ROUNDS: {len(ROUNDS)} = {len(results)}');print(f'GUROBI_VERSION: {gv}');print(f'REFERENCE_FAILURES: {len(rf)}');print(f'GUROBI_CASES_CHECKED: {len(gc)}');print(f'GUROBI_FAILURES: {len(gf)}');print(f'GUROBI_GATE: {gate}');print(f'WORST_EXACT_REGRET: {worst:.15g}');print(f'STRICT_REGRET_TOL: {STRICT_REGRET_TOL:.15g}');print(f'FEAS_TOL: {FEAS_TOL:.15g}');print(f'PWL_POINTS: {R9_PWL_POINTS}');print(f'R9 STATUS: {status}');print('ARTIFACT: r9_end_to_end.json');return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
