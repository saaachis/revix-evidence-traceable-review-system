"""The aspect classifier, and the measurement that says whether it helped.

Proposal section 17, component 2. Until now this was a lexicon: a list of cue
words per topic, matched case-insensitively. ADR 0004 argued for shipping that
first, and it was right, but a lexicon has a ceiling you can see from here. It
cannot know that "showroom guy promised 22 but I get 14" is about fuel economy
unless somebody thought to put "kmpl" in the list, and it will never learn
that "AC struggles in May" is about comfort.

**Trained on weak labels.** The training targets come from the lexicon, over
every real review we hold. That sounds circular and is not, quite: a linear
model over character and word n-grams sees far more than the cue list it was
taught from, so it generalises to phrasings the lexicon misses. Distant
supervision is a standard way to get a first classifier without a labelling
budget, and its honesty depends entirely on the next paragraph.

**Evaluated on hand labels.** The only score that counts is against sentences
a person read and labelled. Evaluating on lexicon output would measure how
well the model memorised the rules. Both the model and the lexicon are scored
on the same held-out human set, so the comparison answers the only question
worth asking: is this better than what it replaces?

Character n-grams alongside word n-grams, because Indian owner reviews are
code-mixed and full of transliterated Hindi. "gaadi", "chalata", "sahi" carry
meaning that a word-level model sees once and never again, while character
n-grams at least share substrings with their variants.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import AspectKey
from revix_core.models import EvidenceUnit
from revix_pipeline.enrichment.extract import ASPECT_CUES, split_sentences
from revix_pipeline.ml.gold import GoldItem

DEFAULT_MODEL_PATH = pathlib.Path("data/models/aspect_classifier.joblib")

#: Below this the model says nothing rather than guessing. A false aspect is
#: worse than a missing one here, because it puts a sentence about the boot
#: into the score for the gearbox and nobody reading the verdict can tell.
DEFAULT_THRESHOLD = 0.45

MIN_TRAINING_SENTENCES = 200


@dataclass(slots=True)
class Evaluation:
    """How a labeller and a system agreed, per topic and overall."""

    name: str
    n_items: int
    macro_f1: float
    micro_f1: float
    per_aspect: dict[str, dict[str, float]] = field(default_factory=dict)
    #: Which topics the macro average covers. A macro F1 over two topics and
    #: one over nine are different claims, and the number alone hides that.
    aspects_scored: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "n_items": self.n_items,
            "macro_f1": round(self.macro_f1, 4),
            "micro_f1": round(self.micro_f1, 4),
            "aspects_scored": self.aspects_scored,
            "per_aspect": {
                k: {m: round(v, 4) for m, v in scores.items()}
                for k, scores in self.per_aspect.items()
            },
        }


class AspectClassifier:
    """Multi-label over the nine topics. One sentence in, zero or more out."""

    def __init__(self, pipeline: Any, threshold: float = DEFAULT_THRESHOLD) -> None:
        self._pipeline = pipeline
        self.threshold = threshold
        # Fixed order, taken from the enum rather than from the training data,
        # so a topic that happened to be absent from one training run does not
        # silently shift every other column.
        self.labels: list[AspectKey] = list(AspectKey)

    def predict(self, sentence: str) -> set[AspectKey]:
        scores = self.predict_proba(sentence)
        return {aspect for aspect, p in scores.items() if p >= self.threshold}

    def predict_proba(self, sentence: str) -> dict[AspectKey, float]:
        raw = self._pipeline.predict_proba([sentence])[0]
        return {aspect: float(raw[i]) for i, aspect in enumerate(self.labels)}

    def save(self, path: pathlib.Path = DEFAULT_MODEL_PATH) -> pathlib.Path:
        import joblib

        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": self._pipeline, "threshold": self.threshold}, path)
        return path

    @classmethod
    def load(cls, path: pathlib.Path = DEFAULT_MODEL_PATH) -> AspectClassifier | None:
        """Returns None when there is no model, rather than raising.

        The extraction stage falls back to the lexicon in that case, which is
        the promise ADR 0004 made: the pipeline runs with nothing trained.
        """
        if not path.exists():
            return None
        import joblib

        blob = joblib.load(path)
        return cls(blob["pipeline"], blob.get("threshold", DEFAULT_THRESHOLD))


def lexicon_aspects(sentence: str) -> set[AspectKey]:
    """What the current rules say. The baseline the model has to beat."""
    lowered = sentence.casefold()
    return {a for a, cues in ASPECT_CUES.items() if any(cue in lowered for cue in cues)}


def build_training_set(
    session: Session, *, exclude: set[str] | None = None
) -> tuple[list[str], list[list[int]]]:
    """Every real sentence, labelled by the lexicon.

    `exclude` holds the gold sentences. They are kept out of training so the
    evaluation is on data the model has never seen, which is the difference
    between a test score and a memory test.
    """
    exclude = exclude or set()
    sentences: list[str] = []
    targets: list[list[int]] = []
    order = list(AspectKey)

    rows = session.scalars(
        select(EvidenceUnit.text).where(
            EvidenceUnit.variant_id.is_not(None) | EvidenceUnit.model_id.is_not(None)
        )
    ).all()

    for text in rows:
        for sentence in split_sentences(text):
            sentence = sentence.strip()
            if len(sentence) < 20 or sentence in exclude:
                continue
            matched = lexicon_aspects(sentence)
            if not matched:
                # Negative examples matter as much as positive ones. Training
                # only on sentences the lexicon matched would teach the model
                # that every sentence is about something.
                sentences.append(sentence)
                targets.append([0] * len(order))
                continue
            sentences.append(sentence)
            targets.append([1 if a in matched else 0 for a in order])

    return sentences, targets


def train_classifier(
    sentences: list[str], targets: list[list[int]], *, seed: int = 20260906
) -> AspectClassifier:
    """Word and character n-grams into one-vs-rest logistic regression.

    Deliberately a linear model. It trains in seconds on a laptop, its
    coefficients can be read to see which words drive a topic, and on a few
    thousand short sentences it is not obviously worse than anything larger.
    A model nobody can inspect would sit badly in a project whose entire
    argument is that you should be able to see why a number is what it is.
    """
    if len(sentences) < MIN_TRAINING_SENTENCES:
        raise ValueError(
            f"only {len(sentences)} training sentences, need at least "
            f"{MIN_TRAINING_SENTENCES}. Ingest more evidence first."
        )

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.pipeline import FeatureUnion, Pipeline

    features = FeatureUnion(
        [
            ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            # Character n-grams for the code-mixed half of the corpus, where
            # "gaadi" and "gadi" are the same word spelled by two people.
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True
                ),
            ),
        ]
    )
    pipeline = Pipeline(
        [
            ("features", features),
            (
                "clf",
                OneVsRestClassifier(
                    LogisticRegression(
                        max_iter=2000,
                        # The topics are wildly imbalanced: everybody writes
                        # about looks, almost nobody about the service centre.
                        # Without this the rare topics are never predicted.
                        class_weight="balanced",
                        random_state=seed,
                    )
                ),
            ),
        ]
    )
    pipeline.fit(sentences, targets)
    return AspectClassifier(pipeline)


def _f1(true_positive: int, false_positive: int, false_negative: int) -> dict[str, float]:
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": float(true_positive + false_negative),
    }


def score_predictions(
    name: str, gold: list[GoldItem], predictions: list[set[AspectKey]]
) -> Evaluation:
    """Per-aspect precision, recall and F1, plus macro and micro averages.

    Macro alongside micro on purpose. Micro is dominated by the common topics,
    so a system that handles looks and mileage well and service badly scores
    respectably on it. Macro treats every topic equally and is the number that
    notices.
    """
    per_aspect: dict[str, dict[str, float]] = {}
    micro_tp = micro_fp = micro_fn = 0

    for aspect in AspectKey:
        tp = fp = fn = 0
        for item, predicted in zip(gold, predictions, strict=True):
            actual = item.aspect_keys
            if aspect in predicted and aspect in actual:
                tp += 1
            elif aspect in predicted:
                fp += 1
            elif aspect in actual:
                fn += 1
        per_aspect[aspect.value] = _f1(tp, fp, fn)
        micro_tp, micro_fp, micro_fn = micro_tp + tp, micro_fp + fp, micro_fn + fn

    # Averaged over the topics this set can actually speak to: those with at
    # least one gold instance, plus any the system predicted, so a false
    # positive on an absent topic still costs something. Averaging over all
    # nine would score a perfect system 0.22 on a set covering two topics,
    # punishing it for questions nobody asked.
    scored = [
        aspect.value
        for aspect in AspectKey
        if per_aspect[aspect.value]["support"] > 0
        or any(aspect in predicted for predicted in predictions)
    ]
    macro = sum(per_aspect[a]["f1"] for a in scored) / len(scored) if scored else 0.0
    return Evaluation(
        name=name,
        n_items=len(gold),
        macro_f1=macro,
        micro_f1=_f1(micro_tp, micro_fp, micro_fn)["f1"],
        per_aspect=per_aspect,
        aspects_scored=scored,
    )


def evaluate_against_gold(
    gold: list[GoldItem], classifier: AspectClassifier | None
) -> list[Evaluation]:
    """Score the lexicon and, if one exists, the classifier on the same set."""
    labelled = [item for item in gold if item.is_labelled]
    if not labelled:
        return []

    results = [score_predictions("lexicon", labelled, [lexicon_aspects(i.text) for i in labelled])]
    if classifier is not None:
        results.append(
            score_predictions(
                "classifier", labelled, [classifier.predict(i.text) for i in labelled]
            )
        )
    return results
