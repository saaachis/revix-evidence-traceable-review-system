# Labelling the gold set

**Read this before touching `data/gold/aspects.jsonl`.**

This is the one task in the project that no tool can do for you, and it is the
task that decides whether any accuracy number we publish means anything.

---

## What it is

A file of real sentences taken from the reviews we ingest, where **a person has
written down which of the nine topics each sentence is actually about**.

## Why it cannot be skipped

The aspect classifier is trained on labels the **lexicon** produced. So if we
measured the classifier against the lexicon, we would be marking an exam with
an answer key the student wrote. It would score around 0.9 and mean nothing.

Only a person can say which of the two is right.

That is why `revix model evaluate` refuses to print a number until somebody has
labelled some sentences. A number without this is a lie with decimals.

**A real example from the first sample.** One sentence was tagged
`service_aftersales` by the lexicon. It was actually about **tyre sizes**: it
mentioned a spare wheel and the word "spare" is near a service cue. No amount
of automation finds that mistake. A person reading it sees it instantly.

---

## Step 1. Get set up

Once, on each of your machines.

```bash
git pull
uv sync --all-packages --extra ml
```

## Step 2. Generate the file

**One person only**, then commit it so everyone labels the same sentences.

```bash
uv run revix gold sample --per-aspect 40
```

Writes `data/gold/aspects.jsonl`, roughly 400 sentences, deliberately spread
across topics rather than drawn at random. A random draw returns a pile of
sentences about looks and mileage and almost nothing about the service centre,
which is the topic this project cares most about.

## Step 3. Split it between the three of you

It is one JSON object per line. Agree who takes which lines, for example:

| Person | Lines |
|---|---|
| Saachi | 1 to 130 |
| Aditya | 131 to 260 |
| Devika | 261 to 400 |

**Then all three of you also label the same 20 lines**, say the first 20. You
will disagree on some of them. That disagreement rate is the ceiling on any
score a classifier can honestly claim, and reporting it is one of the stronger
things you can put in the report. If two people cannot agree what a sentence is
about, no model can be expected to.

## Step 4. Label

For each line, fill in `aspects` and put your name in `labelled_by`:

```json
{"id": "safety-0004", "text": "Brakes felt weak on the highway.", "aspects": ["safety"], "labelled_by": "saachi"}
```

### The nine valid keys, exactly as spelled

| Key | Means |
|---|---|
| `engine_gearbox` | Engine and gearbox |
| `ride_handling_nvh` | Ride quality, handling and noise |
| `running_cost` | Real-world mileage and running cost |
| `space_comfort` | Interior space and comfort |
| `features` | Features and infotainment |
| `build_quality` | Build quality |
| `safety` | Safety |
| `service_aftersales` | Service, after-sales and parts |
| `long_term_reliability` | Long-term reliability |

A typo in a key is an error, not a silent skip: the loader raises rather than
quietly shrinking the set.

### The rules that matter

- **A sentence can have several topics.** `["running_cost", "engine_gearbox"]`
  is perfectly normal and common.
- **An empty list `[]` is a real answer, not a skip.** "The colour is nice" is
  about none of these. Those sentences are valuable, because they teach the
  system what *not* to fire on, and a gold set without them can only measure
  agreement with the rules.
- **Label what the sentence says, not what the review is about.** One sentence
  at a time. The rest of the review is not in front of you on purpose.
- **To genuinely skip one, leave `labelled_by` empty.** It will be ignored.
- **Do not look at what the lexicon thought.** The `id` prefix hints at it.
  Ignore the hint. If you agree with it out of laziness, the gold set becomes
  worthless and so does every number computed from it.

## Step 5. Check progress

```bash
uv run revix gold status
```

Shows how many are labelled and which topics are still thin.

## Step 6. Commit it

`data/gold/aspects.jsonl` is committed on purpose, and `.gitignore` has an
explicit exception for `data/gold/**` to make sure of it.

It is the most expensive artefact in this repository. Everything else can be
recomputed from the sources; this cannot be recomputed from anything.

## Step 7. Train and measure

```bash
uv run revix model train                 # holds the gold sentences out of training
uv run revix model evaluate --record     # scores both systems, writes to eval_run
```

`--record` puts the numbers on the public `/accuracy` page, tagged with the
commit that produced them.

## Step 8. Decide

- **If the classifier wins**, set `ASPECT_CLASSIFIER_ENABLED=true` on Render.
- **If it loses, leave it off and say so.** The first measured comparison had
  the classifier losing to the lexicon by 0.29 macro F1 on twelve sentences.
  "We built a classifier, measured it properly, and it did not beat the simple
  approach, so we did not ship it" is a better result than most projects
  manage, and it is the reason the switch defaults to off.

---

## How long this takes

About 400 sentences, three people, roughly ten seconds each: **an hour or so per
person.**

Do it in one sitting if you can. Labelling standards drift when you come back
to it days later, and a set labelled to two different standards is worse than a
smaller set labelled to one.

---

## Related

- [ADR 0004](adr/0004-lexicon-baseline-before-a-classifier.md), why the lexicon
  shipped first
- [DEVELOPING.md](../DEVELOPING.md), the surrounding workflow
