# 4. A lexicon baseline before a classifier

**Status:** accepted · **Date:** 2026-09-05

## Context

[proposal.md](../proposal.md) section 17 specifies aspect extraction as an
LLM-assisted bootstrap followed by a distilled multilingual classifier,
measured against 500 hand-labelled sentences.

That is the right end state. It is also blocked on 500 hand-labelled
sentences, and everything downstream of extraction is blocked on it: no
opinions means no credibility scoring, no fusion, no verdict, no API and
nothing to show.

## Decision

Ship a transparent lexicon and rule extractor first. Nine cue lists, a
sentiment cue list, negation handling and a hedging penalty.
`extract_from_text` is the seam: the classifier replaces its body and nothing
else in the pipeline changes.

## Consequences

**We gain:** a working pipeline end to end in week one rather than week three,
and an honest baseline. "Our classifier scores 0.79 macro F1" means nothing
without knowing what a keyword matcher scores on the same set. Now we will
know.

**We accept:** the baseline will be poor on code-mixed Hinglish, because a
cue list of English words cannot be anything else. That is a number we
publish rather than hide, and it is the gap the classifier has to close.

**What must not happen:** shipping the baseline and calling it done. The gold
set and the classifier remain a primary objective. This ADR is a sequencing
decision, not a descoping one.
