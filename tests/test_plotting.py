from pathlib import Path

from cchard_eval.data import load_items
from cchard_eval.plotting import create_figures
from cchard_eval.statistics import write_summaries


ROOT = Path(__file__).resolve().parents[1]


def test_creates_three_png_and_three_pdf_figures(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))
    items = load_items(ROOT / "sample_items.json")
    scores = [
        {
            "item_id": item["id"],
            "model_label": "demo",
            "prediction_status": "ok",
            "judge_status": "ok",
            "final_score": 70,
            "synthetic": True,
        }
        for item in items
    ]
    summaries = tmp_path / "summaries"
    write_summaries(items, scores, summaries)
    figures = create_figures(summaries, tmp_path / "figures", synthetic=True)
    assert len(figures) == 6
    assert {path.suffix for path in figures} == {".png", ".pdf"}
    assert all(path.exists() and path.stat().st_size > 1000 for path in figures)
