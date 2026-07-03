import json, pathlib
from jsonschema import Draft202012Validator

SCHEMA = json.loads((pathlib.Path(__file__).parents[1] / "schemas/matra-0.2.json").read_text())

def test_schema_is_valid_jsonschema():
    Draft202012Validator.check_schema(SCHEMA)

def test_v02_deltas_present():
    node = SCHEMA["properties"]["structure"]["items"]["properties"]
    assert "status" in node                      # delta 1: per-matra status
    assert "effective_from" in node              # delta 2
    assert "matra_cid" in node                   # delta 3
    assert "application_scope" in node           # delta 7
    assert "eId" in node                         # Task 6′: AKN-style structural id
    assert "wId" in node                         # Task 6′: = eId at first assignment (v0)
    assert "flat_profile" in SCHEMA["properties"]  # delta 4 (profile descriptor)
    assert SCHEMA["properties"]["schema_version"]["const"] == "0.2"
    assert "machine_translated" in SCHEMA["properties"]["title"]["properties"]
    assert "known_defects" in SCHEMA["properties"]["provenance"]["properties"]
    # x_* = implementation-extension namespace, NOT part of the open standard
    assert not any(k.startswith("x_") for k in SCHEMA["properties"])

def test_minimal_doc_validates():
    doc = json.loads((pathlib.Path(__file__).parent / "fixtures/minimal_doc.json").read_text())
    Draft202012Validator(SCHEMA).validate(doc)
