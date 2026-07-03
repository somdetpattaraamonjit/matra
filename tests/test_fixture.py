import json, pathlib
FIX = pathlib.Path(__file__).parent / "fixtures/criminal_code_sample.jsonl"

def rows():
    return [json.loads(l) for l in FIX.read_text(encoding="utf-8").splitlines() if l.strip()]

def test_fixture_shape():
    rs = rows()
    assert 2 <= len(rs) <= 3
    tl = {r["timeline_code"] for r in rs}
    assert any(t.endswith("-63") for t in tl)
    r63 = next(r for r in rs if r["timeline_code"].endswith("-63"))
    assert {"sections","is_latest","reference_url"} <= set(r63)
    assert len(r63["sections"]) == 80
