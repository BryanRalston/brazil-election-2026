#!/usr/bin/env python3
"""First round (TSE 6257) vs runoff (6258) comparison. Statistical screen, NOT a fraud test."""
import json, os, urllib.request, concurrent.futures as cf, datetime
HERE=os.path.dirname(os.path.abspath(__file__))
B="https://resultados.tse.jus.br/oficial/ele2026/"
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=10))
def parse(d):
    c={}
    for a in d["carg"][0]["agr"]:
        for p in a["par"]:
            for x in p["cand"]: c[x["nmu"]]=int(x["vap"])
    e,v,s=d["e"],d["v"],d["s"]
    lu=c.get("LULA",0); fl=c.get("FLAVIO BOLSONARO",0)
    return dict(est=int(e["est"]),comp=int(e["c"]),tv=int(v["tv"]),vb=int(v["vb"]),vn=int(v["tvn"]),lu=lu,fl=fl,oth=sum(c.values())-lu-fl,pc=float(s["pstn"].replace(",",".")),cand=c)
def f(el,ab):
    try: return parse(get(f"{B}{el}/dados/{ab[:2]}/{ab}-c0001-e00{el}-u.json"))
    except Exception: return None
def pair(ab): return ab,f(6257,ab),f(6258,ab)
cfg=get(B+"6258/config/mun-e006258-cm.json")
ufs=[a["cd"] for a in cfg["abr"] if a["cd"]!="zz"]
names={a["cd"]+m["cd"]:(a["cd"].upper(),m["nm"].title()) for a in cfg["abr"] if a["cd"]!="zz" for m in a["mu"]}
with cf.ThreadPoolExecutor(16) as ex:
    top=list(ex.map(pair,["br"]+ufs+["zz"])); mun=list(ex.map(pair,list(names)))
def summ(r1,r2):
    return dict(r1_turnout=100*r1["comp"]/r1["est"],r2_turnout=100*r2["comp"]/r2["est"],
      r1_bn=100*(r1["vb"]+r1["vn"])/r1["tv"],r2_bn=100*(r2["vb"]+r2["vn"])/r2["tv"],
      r1_lu=100*r1["lu"]/(r1["tv"]-r1["vb"]-r1["vn"]),r1_fl=100*r1["fl"]/(r1["tv"]-r1["vb"]-r1["vn"]),
      r2_lu=100*r2["lu"]/(r2["lu"]+r2["fl"]),d_lu=r2["lu"]-r1["lu"],d_fl=r2["fl"]-r1["fl"],d_comp=r2["comp"]-r1["comp"],
      oth=r1["oth"],d_bn=(r2["vb"]+r2["vn"])-(r1["vb"]+r1["vn"]),r2_pc=r2["pc"])
out={"generated":datetime.datetime.now().isoformat(timespec="seconds"),"states":[]}
for ab,r1,r2 in top:
    if not(r1 and r2): continue
    s=summ(r1,r2); s["uf"]=ab.upper()
    if ab=="br": s["r1_cands"]=sorted(r1["cand"].items(),key=lambda x:-x[1]); out["national"]=s
    else: out["states"].append(s)
flags=[];n=0
for ab,r1,r2 in mun:
    if not(r1 and r2) or r2["pc"]<100 or r1["est"]==0: continue
    n+=1; uf,nm=names[ab]; s=summ(r1,r2)
    # max Lula could add: all R1 other-candidate votes + all R1 blank/null + net new voters
    cap=r1["oth"]+r1["vb"]+r1["vn"]+max(0,s["d_comp"])
    reasons=[]
    if s["d_lu"]>cap and s["d_lu"]>50: reasons.append(f"Lula +{s['d_lu']} > max available {cap} (Flávio-to-Lula switching needed)")
    if s["d_fl"]>r1["oth"]+r1["vb"]+r1["vn"]+max(0,s["d_comp"]) and s["d_fl"]>50: reasons.append(f"Flávio +{s['d_fl']} > max available")
    dt=s["r2_turnout"]-s["r1_turnout"]
    if abs(dt)>=8 and r1["comp"]>=1000: reasons.append(f"turnout {s['r1_turnout']:.1f}%→{s['r2_turnout']:.1f}%")
    if s["r1_bn"]-s["r2_bn"]>=8 and r1["comp"]>=1000: reasons.append(f"blank/null {s['r1_bn']:.1f}%→{s['r2_bn']:.1f}%")
    if reasons: flags.append(dict(uf=uf,municipality=nm,r1_comp=r1["comp"],r2_comp=r2["comp"],d_lu=s["d_lu"],d_fl=s["d_fl"],oth=r1["oth"],turn=dt,reasons=reasons))
out["munis_compared"]=n; out["flags"]=sorted(flags,key=lambda x:-x["r1_comp"])
json.dump(out,open(os.path.join(HERE,"r1_compare.json"),"w"),ensure_ascii=False,indent=1)
print(json.dumps(out["national"],ensure_ascii=False,indent=0)); print(n,len(flags))
for s in sorted(out["states"],key=lambda s:s["r2_lu"]-s["r1_lu"]): print(s["uf"],f"Lu {s['r1_lu']:.1f}->{s['r2_lu']:.1f} T {s['r1_turnout']:.1f}->{s['r2_turnout']:.1f} BN {s['r1_bn']:.1f}->{s['r2_bn']:.1f} pc{s['r2_pc']}")
for x in flags[:40]: print(x)
