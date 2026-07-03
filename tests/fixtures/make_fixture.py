import json, pathlib, sys
RAW = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.home() / ".aice/legalrag/raw/1956-11.jsonl"
OUT = pathlib.Path(__file__).parent / "criminal_code_sample.jsonl"
rows = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
grp = [r for r in rows if "ป0006-1D-0003" in r.get("timeline_code", "")]
grp.sort(key=lambda r: int(r["timeline_code"].rsplit("-", 1)[1]))
keep = [grp[0], grp[-1]]                       # oldest + latest (-63)
keep[-1] = {**keep[-1], "sections": keep[-1]["sections"][:80]}
OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in keep), encoding="utf-8")
print("wrote", OUT, [r["timeline_code"] for r in keep], "sizes:", [len(r["sections"]) for r in keep])
