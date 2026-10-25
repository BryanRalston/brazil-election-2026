#!/usr/bin/env python3
"""Refetch TSE official results (2nd round, election 6258) for Brazil + 27 UFs and merge into data.json."""
import json, urllib.request, datetime, concurrent.futures as cf, os
BASE = "https://resultados.tse.jus.br/oficial/ele2026/6258/dados/{uf}/{uf}-c0001-e006258-u.json"
STATES = [("ac","Acre","North"),("am","Amazonas","North"),("ap","Amapá","North"),("pa","Pará","North"),("ro","Rondônia","North"),("rr","Roraima","North"),("to","Tocantins","North"),
("al","Alagoas","Northeast"),("ba","Bahia","Northeast"),("ce","Ceará","Northeast"),("ma","Maranhão","Northeast"),("pb","Paraíba","Northeast"),("pe","Pernambuco","Northeast"),("pi","Piauí","Northeast"),("rn","Rio Grande do Norte","Northeast"),("se","Sergipe","Northeast"),
("df","Distrito Federal","Center-West"),("go","Goiás","Center-West"),("ms","Mato Grosso do Sul","Center-West"),("mt","Mato Grosso","Center-West"),
("es","Espírito Santo","Southeast"),("mg","Minas Gerais","Southeast"),("rj","Rio de Janeiro","Southeast"),("sp","São Paulo","Southeast"),
("pr","Paraná","South"),("rs","Rio Grande do Sul","South"),("sc","Santa Catarina","South")]
REGIONS = ["North","Northeast","Center-West","Southeast","South"]
HERE = os.path.dirname(os.path.abspath(__file__))
f = lambda s: float(s.replace(",", "."))

def fetch(uf):
    req = urllib.request.Request(BASE.format(uf=uf) + "?t=" + str(datetime.datetime.now().timestamp()), headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=20))
    c = {}
    for a in d["carg"][0]["agr"]:
        for p in a["par"]:
            for x in p["cand"]:
                c["flavio" if "FLAVIO" in x["nmu"] else "lula"] = (int(x["vap"]), f(x["pvapn"]), x.get("e"))
    return {"pct_counted": round(f(d["s"]["pstn"]), 2), "sections_total": int(d["s"]["ts"]), "sections_counted": int(d["s"]["st"]),
            "flavio_pct": round(c["flavio"][1], 2), "flavio_votes": c["flavio"][0], "lula_pct": round(c["lula"][1], 2), "lula_votes": c["lula"][0],
            "elected": [k for k, v in c.items() if v[2] == "s"], "source_time": f"{d['dt']} {d['ht']} " + ("BRT" if uf == "br" else "local time"), "final": d.get("tf") == "s"}

def main():
    path = os.path.join(HERE, "data.json"); data = json.load(open(path))
    with cf.ThreadPoolExecutor(10) as ex:
        res = dict(zip(["br"] + [s[0] for s in STATES], ex.map(lambda u: _safe(u), ["br"] + [s[0] for s in STATES])))
    states = []
    for uf, name, reg in STATES:
        r = res[uf]
        states.append({"uf": uf.upper(), "name": name, "region": reg, **(r or {"unavailable": True, "pct_counted": None, "flavio_pct": None, "lula_pct": None, "source_time": None})})
    regions = []
    for reg in REGIONS:
        ok = [s for s in states if s["region"] == reg and not s.get("unavailable")]
        ts = sum(s["sections_total"] for s in ok); st = sum(s["sections_counted"] for s in ok)
        fv = sum(s["flavio_votes"] for s in ok); lv = sum(s["lula_votes"] for s in ok)
        regions.append({"region": reg, "states_available": len(ok), "pct_counted": round(100*st/ts, 2) if ts else None,
                        "flavio_pct": round(100*fv/(fv+lv), 2) if fv+lv else None, "lula_pct": round(100*lv/(fv+lv), 2) if fv+lv else None,
                        "flavio_votes": fv, "lula_votes": lv})
    br = res["br"]
    if br:
        data.update({"source": "TSE Resultados (official)", "source_time": br["source_time"], "pct_counted": br["pct_counted"],
                     "flavio_pct": br["flavio_pct"], "flavio_votes": br["flavio_votes"], "lula_pct": br["lula_pct"], "lula_votes": br["lula_votes"],
                     "gap_votes": abs(br["flavio_votes"] - br["lula_votes"])})
        if br["elected"]: data["winner_called"] = ("Flávio Bolsonaro" if br["elected"] == ["flavio"] else "Lula") + " elected (TSE)"
    data.update({"states": states, "regions": regions, "states_source": "TSE Resultados per-UF JSON (ele2026/6258)",
                 "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)
    print(f'BR {data["pct_counted"]}% counted | Flávio {data["flavio_pct"]} | Lula {data["lula_pct"]} | states ok {sum(1 for s in states if not s.get("unavailable"))}/27')

def _safe(uf):
    try: return fetch(uf)
    except Exception: return None

if __name__ == "__main__": main()
