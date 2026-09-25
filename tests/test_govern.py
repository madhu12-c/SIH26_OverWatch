"""Governance: sealed audit log, tamper detection, replay under the consent rules."""
import json
import shutil
import subprocess

import pytest

import govern
import paths


@pytest.fixture(scope="module")
def proposals():
    return govern.load_proposals()


@pytest.fixture(scope="module")
def log(proposals):
    return govern.sample_log(proposals)


def test_seal_intact(log):
    assert govern.verify(log)["ok"]


@pytest.mark.parametrize("field", ["note", "verb", "actor", "ts"])
def test_any_edit_breaks_the_seal_at_that_event(log, field):
    k = 3
    bad = [dict(e, **{field: str(e.get(field)) + "x"}) if i == k else e for i, e in enumerate(log)]
    v = govern.verify(bad)
    assert not v["ok"] and v["broken_at"] == k


def test_deleting_an_event_breaks_the_chain(log):
    v = govern.verify(log[:2] + log[3:])
    assert not v["ok"] and v["broken_at"] == 2


def test_replay_is_deterministic(log, proposals):
    assert govern.replay(log, proposals)["digest"] == govern.replay(log, proposals)["digest"]


def test_replay_refuses_what_the_rules_forbid(log, proposals):
    r = govern.replay(log, proposals)
    whys = " ".join(x["why"] for x in r["refused"])
    assert "registrar" in whys                       # a reviewer linking two companies
    assert "can retire" in whys                      # a non-owner retiring a code
    # The forged ACCEPT did not change the registrar's decision.
    assert len(r["state"]["linked"]) == 1


def test_dispute_returns_a_link_to_review(log, proposals):
    r = govern.replay(log, proposals)
    assert all(d["state"] == "BACK TO REVIEW" for d in r["state"]["disputed"].values())
    assert r["state"]["disputed"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_browser_seal_matches_python(log):
    """The portal seals events in JavaScript; govern.py must verify them."""
    script = (
        "import('./ui/src/lib/chain.js').then(({ verify, sha256, canonical }) => {"
        "  const log = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "  const v = verify(log);"
        "  console.log(JSON.stringify({ ok: v.ok, first: sha256(canonical(log[0])) }));"
        "})"
    )
    out = subprocess.run(["node", "-e", script.replace("require('fs')", "process.getBuiltinModule('fs')")],
                         input=json.dumps(log), capture_output=True, text=True, cwd=paths.ROOT, timeout=60)
    res = json.loads(out.stdout)
    assert res["ok"] and res["first"] == log[0]["hash"]
