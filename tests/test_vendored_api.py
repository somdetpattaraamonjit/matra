import json
import os
import pathlib
import subprocess
import sys
import tempfile

from matra.splitter import split_record
from matra.structure import build_docs

FIX = pathlib.Path(__file__).parent / "fixtures/criminal_code_sample.jsonl"
REPO_ROOT = pathlib.Path(__file__).parents[1]


def _row_63():
    rows = [json.loads(l) for l in FIX.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next(r for r in rows if r["timeline_code"].endswith("-63"))


def test_split_record_on_fixture_63():
    docs = split_record(_row_63())
    assert len(docs) >= 2
    assert docs[0]["doc_type"] in {"enacting_act", "code", "act"}


def test_build_docs_returns_list_pair():
    docs, flags = build_docs(_row_63())
    assert isinstance(docs, list)
    assert isinstance(flags, list)


def test_cli_run_on_temp_single_record_json():
    record = _row_63()
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
        assert (out_dir / "qa_report.json").exists()
        assert (out_dir / "docs_v02.json").exists()
        assert (out_dir / "toc_generated.json").exists()
