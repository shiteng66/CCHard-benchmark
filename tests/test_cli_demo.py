import json
import os
from pathlib import Path
import subprocess
import sys

from cchard_eval.data import load_jsonl


ROOT = Path(__file__).resolve().parents[1]


def run_demo(output, tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)
    env["MPLCONFIGDIR"] = str(tmp_path / "mpl")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cchard_eval",
            "demo",
            "--items",
            str(ROOT / "sample_items.json"),
            "--output",
            str(output),
            "--resamples",
            "50",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_demo_runs_end_to_end_and_resumes(tmp_path):
    output = tmp_path / "demo"
    first = run_demo(output, tmp_path)
    assert first.returncode == 0, first.stderr
    assert len(load_jsonl(output / "predictions.jsonl")) == 250
    assert len(load_jsonl(output / "scores.jsonl")) == 250
    assert all(record["synthetic"] is True for record in load_jsonl(output / "scores.jsonl"))
    assert len(list((output / "summaries").glob("*.csv"))) == 5
    assert len(list((output / "figures").glob("*.png"))) == 3
    assert len(list((output / "figures").glob("*.pdf"))) == 3

    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["item_count"] == 250
    assert "api_key" not in json.dumps(manifest).lower()

    second = run_demo(output, tmp_path)
    assert second.returncode == 0, second.stderr
    assert len(load_jsonl(output / "predictions.jsonl")) == 250
    assert len(load_jsonl(output / "scores.jsonl")) == 250
