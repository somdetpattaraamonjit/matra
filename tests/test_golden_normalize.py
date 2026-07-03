import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))  # tests-dir hardening: resolve `canon` regardless of invocation cwd
from canon import canonicalize, get_normalizer

FIX = pathlib.Path(__file__).parent / "fixtures/criminal_code_sample.jsonl"
GOLDEN = pathlib.Path(__file__).parent / "golden/normalize_63.golden.json"


def _row_63():
    rows = [json.loads(l) for l in FIX.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next(r for r in rows if r["timeline_code"].endswith("-63"))


def test_golden_normalize_63_byte_identical():
    normalize = get_normalizer()
    docs, flags = normalize(_row_63())
    actual = canonicalize(docs, flags)

    assert GOLDEN.exists(), f"golden file missing — run tests/make_golden.py first: {GOLDEN}"
    expected = GOLDEN.read_bytes()

    if actual != expected:
        diff = _first_diff_region(expected, actual)
        raise AssertionError(f"normalizer output drifted from golden byte-for-byte:\n{diff}")


def _first_diff_region(expected: bytes, actual: bytes, context: int = 80) -> str:
    """Short unified-diff-style view of the first differing region only."""
    exp_lines = expected.decode("utf-8").splitlines()
    act_lines = actual.decode("utf-8").splitlines()
    for i, (e_line, a_line) in enumerate(zip(exp_lines, act_lines)):
        if e_line != a_line:
            lo = max(0, i - 2)
            hi = i + 3
            lines = [f"first mismatch at line {i + 1}:"]
            for j in range(lo, min(hi, len(exp_lines))):
                marker = ">>>" if j == i else "   "
                lines.append(f"{marker} - {exp_lines[j][:context]}")
            for j in range(lo, min(hi, len(act_lines))):
                marker = ">>>" if j == i else "   "
                lines.append(f"{marker} + {act_lines[j][:context]}")
            return "\n".join(lines)
    if len(exp_lines) != len(act_lines):
        return f"line count differs: expected {len(exp_lines)} lines, got {len(act_lines)} lines"
    return "byte difference with no line-level diff found (whitespace-only?)"
