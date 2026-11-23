def test_target_regression_error_is_vietnamese_and_actionable():
    from signal_tools_gui_v813 import autoeq_error_vn

    message = autoeq_error_vn(
        "No safe 1/4-oct PEQ plan: unacceptable target regression"
    )

    assert "Không tạo được Auto EQ" in message
    assert "1/4 octave" in message
    assert "LF/HF" in message
    assert "số PEQ" in message
    assert "unacceptable target regression" not in message


def test_unknown_solver_error_never_leaks_as_bare_english():
    from signal_tools_gui_v813 import autoeq_error_vn

    message = autoeq_error_vn("solver exploded")

    assert message.startswith("Không tạo được Auto EQ")
    assert "Cách xử lý" in message
    assert "solver exploded" not in message


def test_eq_finish_routes_worker_errors_through_vietnamese_mapper():
    from pathlib import Path

    source = Path("signal_tools_gui_v813.py").read_text(encoding="utf-8")
    finish = source[source.index("    def _finish(self,ticket,future):"):]

    assert "self.warning(autoeq_error_vn(exc))" in finish

