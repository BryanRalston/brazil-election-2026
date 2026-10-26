"""Shared helpers: build/append national snapshot history + per-drop deltas."""
def point(d, source=None):
    return {"time_brt": d.get("source_time"), "source": source or d.get("source"), "pct_counted": d.get("pct_counted"),
            "lula_votes": d.get("lula_votes"), "flavio_votes": d.get("flavio_votes"), "lula_pct": d.get("lula_pct"),
            "flavio_pct": d.get("flavio_pct"), "gap": (d["flavio_votes"] - d["lula_votes"]) if d.get("flavio_votes") is not None and d.get("lula_votes") is not None else None}
def recompute(hist):
    hist.sort(key=lambda p: (p["pct_counted"] or 0, (p["lula_votes"] or 0) + (p["flavio_votes"] or 0)))
    prev = None
    for p in hist:
        if prev:
            dl, df = p["lula_votes"] - prev["lula_votes"], p["flavio_votes"] - prev["flavio_votes"]
            p["batch_votes"] = dl + df; p["batch_lula_votes"] = dl; p["batch_flavio_votes"] = df
            p["batch_lula_share"] = round(100 * dl / (dl + df), 2) if dl + df > 0 else None
        else:
            p["batch_votes"] = p["lula_votes"] + p["flavio_votes"]; p["batch_lula_votes"] = p["lula_votes"]; p["batch_flavio_votes"] = p["flavio_votes"]
            p["batch_lula_share"] = p["lula_pct"]
        prev = p
    return hist
def append(data):
    hist = data.get("history") or []
    if data.get("pct_counted") is not None and all(h["pct_counted"] != data["pct_counted"] for h in hist):
        hist.append(point(data))
    data["history"] = recompute(hist)
