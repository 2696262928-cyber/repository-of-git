from types import SimpleNamespace

from src.evaluator.report_analyzer import apply_image_precheck_penalties
from src.vision.image_processor import ImageLabel


def test_apply_image_precheck_penalties_changes_score():
    diagnostics = {"precheck_score": 100, "precheck_notes": []}
    image_results = [
        SimpleNamespace(
            content_type=SimpleNamespace(label=ImageLabel.CODE_SCREENSHOT),
            quality=SimpleNamespace(is_blurry=True),
            waveform_content=None,
        )
    ]

    updated = apply_image_precheck_penalties(diagnostics, image_results)

    assert updated["precheck_score"] == 94
    assert any("代码/文本截图" in note for note in updated["precheck_notes"])
    assert any("图片质量偏低" in note for note in updated["precheck_notes"])

