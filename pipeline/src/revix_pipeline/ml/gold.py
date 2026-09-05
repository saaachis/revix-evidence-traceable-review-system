"""The hand-labelled set the classifier is measured against.

A classifier trained on lexicon output and evaluated on lexicon output would
score close to perfect and mean nothing: it would be measuring how well it
memorised the rules, not whether the rules were right. The only escape is a
set of sentences a person read and labelled, and that has to be built by hand
because there is no shortcut that is not circular.

So this module does the part that can be automated. It draws a sample worth
labelling and it reads the result back. The labelling itself is yours.

The sample is stratified deliberately. Drawing at random from real evidence
gives you a pile of sentences about looks and mileage, because that is what
people write about, and almost nothing about the service centre, which is the
aspect the whole project cares most about. A model evaluated on that sample
would look fine while being useless at the thing that matters.
"""

from __future__ import annotations

import json
import pathlib
import random
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import AspectKey
from revix_core.models import EvidenceUnit
from revix_pipeline.enrichment.extract import ASPECT_CUES, split_sentences

#: Where the labelled set lives. Committed, because it is the most expensive
#: artefact in the repository: everything else can be recomputed.
DEFAULT_GOLD_PATH = pathlib.Path("data/gold/aspects.jsonl")

#: Sentences shorter than this cannot carry an opinion about a topic, and
#: asking somebody to label them wastes the scarcest resource we have.
MIN_SENTENCE_CHARS = 40
MAX_SENTENCE_CHARS = 400


@dataclass(slots=True)
class GoldItem:
    """One sentence and the topics a person judged it to be about."""

    id: str
    text: str
    aspects: list[str] = field(default_factory=list)
    source_key: str = ""
    #: Left empty by the sampler and filled in by whoever labels it, so that
    #: disagreements between the three of us can be found later rather than
    #: silently averaged.
    labelled_by: str = ""
    notes: str = ""

    @property
    def aspect_keys(self) -> set[AspectKey]:
        out: set[AspectKey] = set()
        for value in self.aspects:
            try:
                out.add(AspectKey(value))
            except ValueError:
                # An unknown label is a typo in the file, and silently dropping
                # it would quietly shrink the gold set.
                raise ValueError(f"unknown aspect '{value}' on gold item {self.id}") from None
        return out

    @property
    def is_labelled(self) -> bool:
        """Labelled means somebody looked, including when the answer is none.

        A sentence about nothing in particular is a real and useful label, so
        the flag is whether a person signed it, not whether the list is empty.
        """
        return bool(self.labelled_by)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "aspects": self.aspects,
            "source_key": self.source_key,
            "labelled_by": self.labelled_by,
            "notes": self.notes,
        }


def load_gold(path: pathlib.Path = DEFAULT_GOLD_PATH) -> list[GoldItem]:
    """Read the set, tolerating a file that does not exist yet."""
    if not path.exists():
        return []
    items: list[GoldItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        raw = json.loads(line)
        items.append(
            GoldItem(
                id=str(raw["id"]),
                text=str(raw["text"]),
                aspects=list(raw.get("aspects") or []),
                source_key=str(raw.get("source_key") or ""),
                labelled_by=str(raw.get("labelled_by") or ""),
                notes=str(raw.get("notes") or ""),
            )
        )
    return items


def save_gold(items: list[GoldItem], path: pathlib.Path = DEFAULT_GOLD_PATH) -> None:
    """JSONL, one item per line, so a merge conflict is one sentence wide."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item.as_dict(), ensure_ascii=False) for item in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cue_aspects(sentence: str) -> set[AspectKey]:
    """Which topics the lexicon thinks this sentence mentions.

    Used only to spread the sample across topics. It is never written into the
    file as a label, because a sample stratified by the lexicon is fine while
    a gold set labelled by the lexicon is worthless.
    """
    lowered = sentence.casefold()
    return {a for a, cues in ASPECT_CUES.items() if any(cue in lowered for cue in cues)}


def sample_for_labelling(
    session: Session,
    *,
    per_aspect: int = 40,
    seed: int = 20260906,
    existing: list[GoldItem] | None = None,
) -> list[GoldItem]:
    """Draw a spread of real sentences worth a person's time.

    Stratified by the aspect the lexicon believes each sentence is about, so
    the rarer topics are represented at all. Service and long-term reliability
    are the two the proposal says dominate Indian ownership, and they are also
    the two that a random draw barely returns.

    A bucket of sentences the lexicon matched to nothing is included on
    purpose. Those are where a classifier can beat a lexicon, and a gold set
    that omits them can only ever measure agreement with the rules.
    """
    rng = random.Random(seed)
    seen_text = {item.text for item in (existing or [])}

    buckets: dict[str, list[tuple[str, str]]] = {a.value: [] for a in AspectKey}
    buckets["none"] = []

    rows = session.execute(
        select(EvidenceUnit.text, EvidenceUnit.source_id).where(
            EvidenceUnit.variant_id.is_not(None) | EvidenceUnit.model_id.is_not(None)
        )
    ).all()

    for text, source_id in rows:
        for sentence in split_sentences(text):
            sentence = sentence.strip()
            if not MIN_SENTENCE_CHARS <= len(sentence) <= MAX_SENTENCE_CHARS:
                continue
            if sentence in seen_text:
                continue
            seen_text.add(sentence)
            matched = _cue_aspects(sentence)
            if matched:
                for aspect in matched:
                    buckets[aspect.value].append((sentence, str(source_id)))
            else:
                buckets["none"].append((sentence, str(source_id)))

    drawn: list[GoldItem] = []
    for name, pool in buckets.items():
        rng.shuffle(pool)
        for sentence, source_id in pool[:per_aspect]:
            drawn.append(
                GoldItem(
                    id=f"{name}-{len(drawn):04d}",
                    text=sentence,
                    aspects=[],
                    source_key=source_id,
                )
            )
    rng.shuffle(drawn)
    return drawn


def coverage(items: list[GoldItem]) -> dict[str, int]:
    """How much of the set is labelled, and how thin each topic is."""
    stats = {"total": len(items), "labelled": 0, "unlabelled": 0, "with_no_aspect": 0}
    for aspect in AspectKey:
        stats[aspect.value] = 0
    for item in items:
        if not item.is_labelled:
            stats["unlabelled"] += 1
            continue
        stats["labelled"] += 1
        if not item.aspects:
            stats["with_no_aspect"] += 1
        for aspect in item.aspect_keys:
            stats[aspect.value] += 1
    return stats
