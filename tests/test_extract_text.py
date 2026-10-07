"""Sentence splitting and sentiment, the lexicon path.

ADR 0004 promised the pipeline keeps running with nothing trained, so the cue
lexicon has to stand on its own. These assert the three readings that were
wrong at some point: an ellipsis read as four sentence endings, a negated
positive read as praise, and a topic mentioned without any opinion counted as
one.
"""

from __future__ import annotations

from revix_core.enums import AspectKey
from revix_pipeline.enrichment.extract import (
    aspects_in,
    extract_from_text,
    score_sentence,
    split_sentences,
)


class TestSplitting:
    def test_an_ellipsis_is_one_pause_not_four_endings(self) -> None:
        text = "The ride quality is genuinely good..... The gearbox eventually failed."
        assert split_sentences(text) == [
            "The ride quality is genuinely good.",
            "The gearbox eventually failed.",
        ]

    def test_fragments_too_short_to_carry_an_opinion_are_dropped(self) -> None:
        assert split_sentences("Ok. Fine. The engine pulls cleanly at low revs.") == [
            "The engine pulls cleanly at low revs."
        ]


class TestSentenceSentiment:
    def test_praise_reads_positive_and_gains_confidence_with_more_cues(self) -> None:
        polarity, confidence = score_sentence("The gearbox is superb and the engine is fantastic.")
        assert polarity == 1.0
        assert confidence > 0.5

    def test_a_negator_flips_the_sentiment(self) -> None:
        # Two positive cues, so praise is the naive reading; the negator pulls
        # it back under zero instead.
        polarity, _ = score_sentence("I would not call it superb or fantastic.")
        assert polarity < 0.0

    def test_a_hedge_lowers_confidence(self) -> None:
        _, hedged = score_sentence("Maybe the engine is superb.")
        _, plain = score_sentence("The engine is superb.")
        assert hedged < plain

    def test_a_sentence_with_no_cue_is_neutral_and_barely_confident(self) -> None:
        assert score_sentence("The colour is a muted shade of grey.") == (0.0, 0.15)


class TestAspectsAndExtraction:
    def test_a_drivetrain_sentence_is_tagged_to_the_drivetrain(self) -> None:
        assert AspectKey.ENGINE_GEARBOX in aspects_in("The gearbox shifts smoothly.")

    def test_an_evaluative_sentence_yields_a_traceable_extraction(self) -> None:
        out = extract_from_text("The gearbox is superb. The seats are a plain grey.")
        assert any(e.aspect == AspectKey.ENGINE_GEARBOX and e.polarity > 0 for e in out)
        # Every extraction carries the sentence it came from.
        assert all(e.span for e in out)

    def test_a_topic_mentioned_without_an_opinion_is_not_an_extraction(self) -> None:
        # Mentions the gearbox but says nothing evaluative, so confidence is
        # below the floor and nothing is emitted.
        assert extract_from_text("There is a gearbox fitted to this car.") == []
