#!/usr/bin/env python3
"""Neutral statistical screen of 2026 runoff municipal results (TSE, election 6258) vs the 2022 runoff
(TSE open data, election 545, cached in .cache2022/baseline2022_r2_mun.json). NOT a fraud test.
Run after update_states.py:  python3 anomalies.py"""
import json, os, urllib.request, statistics, datetime, collections, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))
R = "https://resultados.tse.jus.br/oficial/ele2026/6258"
f = lambda s: float(str(s).replace(",", "."))
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=8))

def muni(uf, cd):
    try:
        d = get(f"{R}/dados/{uf}/{uf}{cd}-c0001-e006258-u.json")
    except Exception:
        return None
    fl = lu = 0
    for a in d["carg"][0]["agr"]:
        for p in a["par"]:
            for x in p["cand"]:
                if "FLAVIO" in x["nmu"]: fl = int(x["vap"])
                else: lu = int(x["vap"])
    e, v, s = d["e"], d["v"], d["s"]
    return {"cd": cd, "pct_counted": f(s["pstn"]), "est": int(e["est"]), "comp": int(e["c"]), "tv": int(v["tv"]),
            "bn": int(v["vb"]) + int(v["tvn"]), "fl": fl, "lu": lu}

def main():
    base = json.load(open(os.path.join(HERE, ".cache2022", "baseline2022_r2_mun.json")))
    cfg = get(f"{R}/config/mun-e006258-cm.json")
    jobs = [(a["cd"], m["cd"], m["nm"]) for a in cfg["abr"] if a["cd"] != "zz" for m in a["mu"]]
    names = {cd: (uf, nm) for uf, cd, nm in jobs}
    with cf.ThreadPoolExecutor(16) as ex:
        res = [r for r in ex.map(lambda j: muni(j[0], j[1]), jobs) if r]
    flags, swings = [], collections.defaultdict(list)
    rows = []
    for r in res:
        uf, nm = names[r["cd"]]; b = base.get(r["cd"])
        if r["pct_counted"] <= 0 or r["est"] == 0: continue
        val = r["fl"] + r["lu"]; turnout = 100 * r["comp"] / r["est"]
        fsh = 100 * r["fl"] / val if val else None
        bnsh = 100 * r["bn"] / r["tv"] if r["tv"] else None
        b_t = b_f = b_bn = None
        if b and b["aptos"] and b["lula"] + b["bolso"]:
            b_t = 100 * b["comp"] / b["aptos"]; b_f = 100 * b["bolso"] / (b["lula"] + b["bolso"])
            b_bn = 100 * (b["brancos"] + b["nulos"]) / b["comp"] if b["comp"] else None
        row = dict(uf=uf.upper(), municipality=nm.title(), pc=r["pct_counted"], comp=r["comp"], val=val, turnout=turnout,
                   fsh=fsh, bnsh=bnsh, b_t=b_t, b_f=b_f, b_bn=b_bn)
        if fsh is not None and b_f is not None and val >= 2000:
            row["swing"] = fsh - b_f; swings[uf].append(row["swing"])
        rows.append(row)
    def add(row, metric, value, baseline, note, sev):
        flags.append({"uf": row["uf"], "municipality": row["municipality"], "metric": metric, "value": round(value, 2),
                      "baseline": None if baseline is None else round(baseline, 2), "pct_counted": round(row["pc"], 1),
                      "votes_counted": row["comp"], "note": note, "_sev": sev})
    stat = {uf: (statistics.median(v), statistics.pstdev(v)) for uf, v in swings.items() if len(v) >= 5}
    for row in rows:
        uf = row["uf"].lower()
        if row["comp"] >= 500 and row["turnout"] >= 95:
            add(row, "turnout_pct", row["turnout"], row["b_t"], "Turnout ≥95% of registered voters in counted sections", row["turnout"] - 90)
        if row["comp"] >= 1000 and row["b_t"] is not None and row["turnout"] - row["b_t"] >= 15:
            add(row, "turnout_jump_pts", row["turnout"] - row["b_t"], row["b_t"], "Turnout up ≥15 pts vs 2022 runoff", row["turnout"] - row["b_t"])
        if "swing" in row and uf in stat:
            med, sd = stat[uf]; dev = row["swing"] - med
            if abs(dev) >= 25 or (sd > 0 and abs(dev) / sd >= 3 and abs(dev) >= 8):
                add(row, "flavio_swing_vs_2022_pts", row["swing"], med,
                    f"Flávio share {row['fsh']:.1f}% vs Bolsonaro {row['b_f']:.1f}% in 2022; state median swing {med:+.1f} pts (deviation {dev/sd if sd else 0:.1f} SD)", abs(dev))
        if row["fsh"] is not None and row["val"] >= 1000 and max(row["fsh"], 100 - row["fsh"]) >= 97:
            who = "Flávio" if row["fsh"] >= 50 else "Lula"
            add(row, f"{who.lower()}_share_pct", max(row["fsh"], 100 - row["fsh"]), None if row["b_f"] is None else (row["b_f"] if who == "Flávio" else 100 - row["b_f"]),
                f"{who} ≥97% of valid votes", 30)
        if row["bnsh"] is not None and row["comp"] >= 1000 and row["b_bn"] is not None and row["bnsh"] - row["b_bn"] >= 10:
            add(row, "blank_null_pct", row["bnsh"], row["b_bn"], "Blank+null share up ≥10 pts vs 2022 runoff", row["bnsh"] - row["b_bn"])
    flags.sort(key=lambda x: -x["_sev"])
    for x in flags: x.pop("_sev")
    by = collections.Counter(x["metric"].split("_")[0] if "share" in x["metric"] else x["metric"] for x in flags)
    p = os.path.join(HERE, "data.json"); data = json.load(open(p))
    data["anomalies"] = flags[:60]
    data["anomaly_summary"] = {"checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "municipalities_fetched": len(res), "municipalities_with_counted_sections": len(rows), "municipalities_total": len(jobs),
        "with_2022_baseline": sum(1 for r in rows if r["b_f"] is not None), "flags_total": len(flags), "flags_by_metric": dict(by),
        "source_2026": "TSE Resultados municipal JSON (ele2026/6258)", "source_2022": "TSE open data, 2022 runoff (detalhe_votacao_munzona + votacao_partido_munzona, cargo Presidente, turno 2)",
        "caveat": "Statistical screen only, not evidence of fraud. Partial counts can be unrepresentative; small or remote municipalities often show extreme margins or turnout naturally."}
    json.dump(data, open(p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(data["anomaly_summary"], ensure_ascii=False))
if __name__ == "__main__": main()
