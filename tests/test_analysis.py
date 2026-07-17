from services.analysis import analyze_scores, calculate_overall_band


def test_overall_band_rounds_quarter_up() -> None:
    scores = {"listening": 6.5, "reading": 6.5, "writing": 6.0, "speaking": 6.0}
    assert calculate_overall_band(scores) == 6.5


def test_analysis_returns_all_tied_lowest_subjects() -> None:
    scores = {"listening": 7.0, "reading": 6.5, "writing": 5.5, "speaking": 5.5}
    result = analyze_scores(scores)
    assert result.lowest_score == 5.5
    assert result.lowest_subjects == ("writing", "speaking")
    assert set(result.recommendations) == {"writing", "speaking"}
