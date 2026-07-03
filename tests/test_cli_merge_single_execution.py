# Task 4'.2 review — Finding 3 (Important): CLI double-merge. Before this fix,
# `matra.cli.main` with --merge called `build_docs(record, merge=True)` (which
# runs `merge.merge_amendments` once internally to build the tree) and THEN
# separately re-ran `splitter.split_record` + `merge.merge_amendments` a
# SECOND time just to obtain the merge_report for qa. Both executions were of
# a pure function so results always agreed, but the merge ran twice, and
# structurally the docs written to disk and the report folded into qa were
# outputs of two different calls rather than one shared one.
#
# The fix: `structure.build_docs_merged(record) -> (docs, flags, merge_report)`
# runs split + merge exactly once; `build_docs(record, merge=True)` now
# delegates to it (discarding the report, back-compat contract preserved);
# the CLI's --merge path calls `build_docs_merged` once.
#
# This test proves SINGLE EXECUTION end-to-end via the real CLI subprocess
# (matches the tests/test_vendored_api.py subprocess pattern) on the portable
# synthetic fixture: qa_report.json's checks.merge.segments_applied == 3 (the
# exact count the fixture is hand-designed to produce) is only obtainable if
# the CLI's build_docs_merged call and the report folded into qa came from the
# SAME run — a stale/mismatched second execution would either crash (module
# import cost aside, it wouldn't diverge since merge_amendments is pure and
# idempotent-safe on non-yet-merged input) or, more informatively, this test
# also monkeypatches merge_amendments to prove it is invoked exactly ONCE per
# CLI process (not twice) — the actual regression this finding was about.
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
import matra
from matra.structure import build_docs, build_docs_merged
from matra.qa import qa_check

FIX = pathlib.Path(__file__).parent / "fixtures/merge_synthetic.json"
REPO_ROOT = pathlib.Path(__file__).parents[1]


def _record():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k != "_comment"}


def test_build_docs_merged_exported_from_package_root():
    assert hasattr(matra, "build_docs_merged")
    assert matra.build_docs_merged is build_docs_merged


def test_build_docs_merged_returns_docs_flags_report_tuple():
    docs, flags, merge_report = build_docs_merged(_record())
    assert isinstance(docs, list)
    assert isinstance(flags, list)
    assert isinstance(merge_report, dict)
    assert merge_report["segments_applied"] == 3


def test_build_docs_merge_true_delegates_and_matches_build_docs_merged():
    """build_docs(record, merge=True) must produce the SAME docs/flags as the
    docs/flags half of build_docs_merged (back-compat contract) — proving the
    delegation is real, not a parallel reimplementation that could drift."""
    record = _record()
    docs_a, flags_a = build_docs(record, merge=True)
    docs_b, flags_b, _report = build_docs_merged(record)

    def _strip(ds):
        out = json.loads(json.dumps(ds))
        for d in out:
            d["provenance"]["ingested_at"] = "SENTINEL"
        return out

    assert _strip(docs_a) == _strip(docs_b)
    assert flags_a == flags_b


def test_merge_amendments_invoked_exactly_once_per_build_docs_merged_call(monkeypatch):
    """Direct proof of single execution: monkeypatch merge.merge_amendments
    with a call-counting wrapper and confirm build_docs_merged invokes it
    exactly once (this is the precise regression Finding 3 was about — the
    old CLI path invoked the equivalent of this twice per process)."""
    import matra.merge as merge_mod
    import matra.structure as structure_mod

    calls = {"n": 0}
    real = merge_mod.merge_amendments

    def _counting(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(merge_mod, "merge_amendments", _counting)
    # structure.build_docs_merged does `from .merge import merge_amendments` at
    # call time (a local import), so patching the merge module attribute is
    # sufficient — the local import resolves the patched name at call time.
    docs, flags, report = structure_mod.build_docs_merged(_record())
    assert calls["n"] == 1, f"merge_amendments must run exactly once, ran {calls['n']} times"
    assert report["segments_applied"] == 3


def test_cli_merge_flag_single_execution_via_subprocess():
    """End-to-end: run the real CLI (`python3 -m matra.cli ... --merge`) on
    the synthetic fixture and assert qa_report.json's checks.merge.
    segments_applied == 3 — the exact count only a correctly single-executed,
    real merge_report (not a stale/mismatched second run) can produce."""
    record = _record()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        raw_record_path = tmp_path / "raw_record.json"
        raw_record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        out_dir = tmp_path / "out"

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "matra.cli", str(raw_record_path), str(out_dir), "--merge"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert (out_dir / "qa_report.json").exists()
        assert (out_dir / "docs_v02.json").exists()
        assert (out_dir / "toc_generated.json").exists()

        qa_report = json.loads((out_dir / "qa_report.json").read_text(encoding="utf-8"))
        checks = qa_report["hard_checks"]
        assert "merge" in checks, f"checks missing 'merge' key: {list(checks)}"
        assert checks["merge"]["segments_applied"] == 3, (
            f"expected 3 segments_applied (proof of the single-execution path carrying "
            f"the real report), got {checks['merge']['segments_applied']}"
        )
        assert checks["merge_conservation_ok"] is True
        assert qa_report["hard_fail"] is False

        docs_v02 = json.loads((out_dir / "docs_v02.json").read_text(encoding="utf-8"))
        code = next(d for d in docs_v02 if d["doc_type"] == "code")
        matra_numbers = {n["number_arabic"] for n in code["structure"] if n["node_type"] == "matra"}
        for want in ["100/1", "100/2", "101/1", "200"]:
            assert want in matra_numbers


def test_cli_no_merge_flag_unchanged_no_merge_key():
    """Without --merge, checks must NOT carry a 'merge' key (byte-identical
    golden safety path, merge.py never imported)."""
    record = _record()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        raw_record_path = tmp_path / "raw_record.json"
        raw_record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        out_dir = tmp_path / "out"

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "matra.cli", str(raw_record_path), str(out_dir)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        qa_report = json.loads((out_dir / "qa_report.json").read_text(encoding="utf-8"))
        assert "merge" not in qa_report["hard_checks"]
        assert "merge_conservation_ok" not in qa_report["hard_checks"]
