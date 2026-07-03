import json, pathlib

# one-time extractor (same pattern as make_fixture.py): finds each record by
# timeline_code in its source month-file, writes the record verbatim to
# tests/fixtures/gate_regressions/<timeline_code>.json. Source month-files are
# READ-ONLY (~/.aice/legalrag/work/sampling_dl/); never edited, only read.
SRC_DIR = pathlib.Path.home() / ".aice/legalrag/work/sampling_dl"
OUT_DIR = pathlib.Path(__file__).parent / "gate_regressions"

# (timeline_code, source month-file) — the 4 groups the 2026-07-02 sampling
# gate failed (typeIds 13/18/20 outside body_types inflating rows_out/chars).
TARGETS = [
    ("ว0018-1B-0017-01", "1913-08.jsonl"),
    ("ว0020-1B-0003-07", "1950-11.jsonl"),
    ("ว0025-1B-0001-00", "1962-07.jsonl"),
    ("อท019-1B-0001-00", "1962-07.jsonl"),
]

# Task 3.5 (2026-07-03): records with sections: [] exist in the real corpus —
# 28 found by a population-scale scan of sampling_dl (27 in 1913-08.jsonl,
# 2 in 2020-01.jsonl) — and crash qa.qa_check's primary_doc() with
# ValueError: max() arg is an empty sequence (normalize_record returns
# ([], []) for them). One real one, extracted verbatim, same as TARGETS.
EMPTY_TARGETS = [
    ("ก0016-1B-0001-16", "1913-08.jsonl"),
]


def find_record(timeline_code, fname):
    path = SRC_DIR / fname
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("timeline_code") == timeline_code:
                return r
    raise SystemExit(f"NOT FOUND: {timeline_code} in {fname}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for tl, fname in TARGETS + EMPTY_TARGETS:
        record = find_record(tl, fname)
        out_path = OUT_DIR / f"{tl}.json"
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {out_path} ({len(record['sections'])} sections)")


if __name__ == "__main__":
    main()
