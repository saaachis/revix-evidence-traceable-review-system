# Milestone 2 — Wireframe Demo

**Revix** · *driven by reviews.*
Planning document: what we will build, how, by whom, and by when.

| | |
|---|---|
| **Milestone** | 2 — Wireframe Demo |
| **Starts** | Monday 3 August 2026 |
| **Demo date** | **Friday 14 August 2026** |
| **Working days** | 10 |
| **Team** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |
| **Previous milestone** | Review 1 — [concept, market gap and literature review](01-concept-market-gap-and-literature-review.md), 31 July 2026 |
| **Full design document** | [docs/proposal.md](../proposal.md) |

---

## Contents

1. [What a wireframe demo is](#1-what-a-wireframe-demo-is)
2. [Why it matters for this project specifically](#2-why-it-matters-for-this-project-specifically)
3. [What we will hand over](#3-what-we-will-hand-over)
4. [How detailed the wireframes should be](#4-how-detailed-the-wireframes-should-be)
5. [Which screens, and how much they matter](#5-which-screens-and-how-much-they-matter)
6. [What each screen must show](#6-what-each-screen-must-show)
7. [The one interaction we must demonstrate](#7-the-one-interaction-we-must-demonstrate)
8. [Who does what](#8-who-does-what)
9. [Timeline, day by day](#9-timeline-day-by-day)
10. [How we will work](#10-how-we-will-work)
11. [Definition of done](#11-definition-of-done)
12. [The demo itself](#12-the-demo-itself)
13. [Risks](#13-risks)
14. [Decisions we still have to make](#14-decisions-we-still-have-to-make)

---

## 1. What a wireframe demo is

A **wireframe** is a drawing of a screen that shows *what goes where and why*, before anyone writes a line of code. It answers questions about structure, not about looks.

The point is that it is cheap to change. Moving a box in a drawing takes ten seconds. Moving the same box after it is built takes a day.

| A wireframe **is** | A wireframe **is not** |
|---|---|
| A layout: what appears on the screen, and where | A finished visual design |
| A hierarchy: what the eye should reach first, second, third | A choice of colours, fonts or logo |
| A set of interactions: what happens when you click a thing | Working software |
| Annotated: notes saying where each number comes from | Real data — everything is realistic placeholder content |
| An argument about *the product* | An argument about *taste* |

**A wireframe demo** is us walking our mentor through those screens in order, as if we were a user, explaining the reasoning behind each decision — and being told where the reasoning is wrong while it is still cheap to fix.

### A tiny example of the difference

The same information, laid out two ways:

```
   LAYOUT A                             LAYOUT B
   ──────────────────────────           ──────────────────────────
   Ride and comfort      8.6            Gearbox           6.2  ⚠ split
   Engine                8.4            Service           5.9  ⚠ split
   Features              8.1            Mileage           7.1
   Mileage               7.1            Engine            8.4
   Gearbox               6.2            Features          8.1
   Service               5.9            Ride and comfort  8.6

   sorted by score                      sorted by disagreement
   "this car is good"                   "here is what you must decide about"
```

Both are correct. Layout B is our product and Layout A is every competitor. **That is a wireframe decision, not a code decision**, and this milestone is where we make and defend it.

---

## 2. Why it matters for this project specifically

Revix is unusual in that **the interface *is* the argument.** Our whole claim is that a verdict should show its trust weighting, its uncertainty and its evidence. If those three things are not legible on screen, the project has failed regardless of how good the pipeline is.

| Our claim | The screen has to prove it |
|---|---|
| "We weigh reviews by trust, not by star average" | A visible switch that changes every number when flipped |
| "We state our confidence honestly" | A range on the screen, not a single decimal |
| "Every number is traceable" | Every number is clickable, and clicking shows the actual reviews |
| "Disagreement is the useful signal" | The most-disagreed-upon topic sits at the top, not the highest-scoring one |

Getting this wrong in week 2 is free. Getting it wrong in week 11 is fatal.

---

## 3. What we will hand over

| # | Deliverable | Meaning |
|---|---|---|
| 1 | **Wireframes for all seven screens** | One drawing per screen, annotated |
| 2 | **A click-through flow** | The four main screens linked so a viewer can move between them like a real user, rather than watching a slideshow |
| 3 | **A screen map** | One page showing how all screens connect, so the whole product is visible at once |
| 4 | **The weighting toggle in both states** | The same screen drawn twice, "equal" and "by credibility", with the changed numbers highlighted. This is the centrepiece. |
| 5 | **Annotations on every number** | A note saying where that value comes from — which source, computed by which stage |
| 6 | **Two worked examples** | One car and one two-wheeler, so the design is proven to work for both |
| 7 | **A five-minute walkthrough script** | Rehearsed, so the demo is a demonstration and not a discussion |
| 8 | **Exports committed to the repository** | PNG or PDF under `docs/wireframes/`, so the work is versioned and reviewable even without the design tool |

---

## 4. How detailed the wireframes should be

Design fidelity comes in three levels. Choosing the wrong one wastes days.

| Level | What it looks like | Time cost | Right for us? |
|---|---|---|---|
| **Low fidelity** | Grey boxes and placeholder lines. No real words. | Hours | For the first two days only |
| **Mid fidelity** | Real labels, realistic numbers, correct hierarchy, still greyscale | Days | **Yes — this is our target** |
| **High fidelity** | Final colours, fonts, icons, spacing, shadows | Weeks | No. Wasted work at this stage |

**We are targeting mid fidelity.** Realistic content, greyscale, correct structure.

The reason is specific to us: our screens are dense with **numbers, ranges and comparisons**. Grey boxes cannot show whether "7.8 with a range of 7.1 to 8.4" is readable at a glance — only real numbers can. But colour choices would be pure decoration at this stage, and would invite feedback about colours instead of about structure.

**One deliberate exception.** We will use a single accent treatment for the weighting toggle and the disagreement markers, because those two things must read as "important" for the demo to make its point.

---

## 5. Which screens, and how much they matter

| Priority | Screen | Purpose | Why this priority |
|---|---|---|---|
| **Must** | **Verdict** | The product. One vehicle, scored topic by topic. | If only one screen existed, this is it |
| **Must** | **Evidence drawer** | The reviews behind any number, with their weights | This is what makes traceability real rather than claimed |
| **Must** | **Compare** | Two or three vehicles side by side | Where overlapping ranges say "too close to call" |
| **Must** | **Landing / search** | Find a vehicle, in one box | The entry point; without it the flow does not start |
| **Should** | **Metrics** | Our own accuracy numbers, in public | Directly targets the honesty argument |
| **Should** | **Method** | Plain-language explanation of how scores are computed | The screen that answers "why should I believe this?" |
| **Should** | **Admin** | Source health, which connectors are alive | Shows the operational engineering behind the product |
| **Won't** | Accounts, settings, watchlists, mobile app | — | Explicitly out of scope. Do not draw them. |

**The cut rule, agreed now rather than on 13 August:** if we are behind on the Friday 7 August checkpoint, the *Should* screens drop to rough sketches and every remaining hour goes into Verdict, Evidence and Compare. **The verdict screen and the weighting toggle are never cut.**

---

## 6. What each screen must show

### 6.1 Verdict — the screen that matters

```
┌──────────────────────────────────────────────────────────────────────┐
│  Hyundai Creta SX (O) 1.5 Diesel AT              Rs 19.2L - 20.4L    │  <- exact variant, never just "Creta"
│                                                                       │
│  ████████████░░░░  7.8 / 10        [ 7.1 ─────── 8.4 ]               │  <- a range, never one decimal
│  412 reviews · 6 sources · updated 2 days ago                        │  <- the evidence base, stated
│                                                                       │
│  Weighting:  [ Equal ]  [ By source ]  [ ✓ By credibility ]          │  <- THE control
├──────────────────────────────────────────────────────────────────────┤
│  ⚠ MOST DISAGREEMENT                                                 │  <- conflict first, by design
│  Gearbox and transmission      6.2  [5.4 ── 7.1]      divergence 0.61│
│  71% of the split is explained by transmission type.                 │  <- we say WHY, not just that
│  Automatic owners: 6.2   ·   Manual owners: 8.8      [ 34 reviews ▾ ]│  <- click opens the drawer
├──────────────────────────────────────────────────────────────────────┤
│  Ride and comfort              8.6  [8.2 ── 8.9]      divergence 0.12│
│  Service and after-sales       5.9  [5.1 ── 6.6]      divergence 0.44│
│  Real-world mileage           17.2 kmpl   claimed 21.4  (−19.6%)     │  <- claimed vs real, always
├──────────────────────────────────────────────────────────────────────┤
│  EXPERT vs OWNER                                                      │
│  Media 8.9  ████████████████░░   Owners 7.4  █████████████░░░░░       │
│  Largest gap: service and after-sales (media 8.5, owners 5.9)        │
├──────────────────────────────────────────────────────────────────────┤
│  OFFICIAL RECORD                                                      │
│  Bharat NCAP 5★ adult / 4★ child  ·  1 recall (2024, fuel pump)      │
└──────────────────────────────────────────────────────────────────────┘
```

| Must show | Why |
|---|---|
| The **exact variant name**, never just the model | Our whole matching problem exists because variants differ |
| An overall score **with a range** | A single decimal implies a precision we do not have |
| Review count, source count, last updated | The user should always know how thin the evidence is |
| The **weighting switch**, visually prominent | This is the product's identity |
| Topic cards ordered by **disagreement** | Deliberately the opposite of every competitor |
| A one-line explanation of *what* explains each split | "71% explained by transmission" is the most useful line on the page |
| Claimed vs real mileage | Instantly legible, useful, and shown by nobody today |
| Expert opinion against owner opinion | Makes the media/owner gap visible |
| The official record — safety and recalls | Joins consumer opinion to objective fact |
| A visible state for **thin evidence** | Draw what a vehicle with only 11 reviews looks like. We suppress rather than publish a bad score, and the wireframe must show that honestly. |

### 6.2 Evidence drawer — where traceability becomes real

Opens when any number is clicked. It slides over the verdict screen rather than navigating away, so the user never loses their place.

| Must show | Why |
|---|---|
| Which number was clicked, restated at the top | Otherwise the user forgets what they are looking at |
| The actual reviews that produced it | The whole point |
| **The weight each review contributed**, sorted heaviest first | This is what "credibility weighting" looks like in practice |
| Why each review was weighted the way it was | e.g. "verified owner · 3 years · 46,000 km" — one line, plain words |
| Source name and an outbound link to the original | Attribution, and it is what makes us respectful of the sources |
| A low-credibility review, deliberately included | Showing one *down-weighted* review is more convincing than showing five good ones |

### 6.3 Compare

| Must show | Why |
|---|---|
| Two or three variants, aspect by aspect | The comparison a buyer actually makes |
| Confidence ranges drawn, not just scores | So overlap is visible |
| **An explicit "too close to call" state** where ranges overlap | The single most honest thing in the product, and something no comparison site will ever say |
| A car-vs-car and a bike-vs-bike example | Proves the design works for both classes |

### 6.4 Landing / search

| Must show | Why |
|---|---|
| One search box, over make / model / variant | Three clicks to a verdict is the target |
| The variant picker — what happens when a model has 14 variants | This is the moment our variant-level design becomes visible to the user |
| A few featured verdicts | Gives the empty state something to be |
| Nothing else | Restraint is a design decision worth defending out loud |

### 6.5 Metrics, Method and Admin — the *Should* screens

| Screen | Must show |
|---|---|
| **Metrics** | Our accuracy per component, and a trend line over time. Including the numbers that are bad. |
| **Method** | How a score is computed, in plain language, with one worked example. No formulas on this screen. |
| **Admin** | One card per source: alive or stale, last run, reviews collected, last error. Plus **one source deliberately shown as failing**, to demonstrate that a dead source degrades the product without breaking it. |

---

## 7. The one interaction we must demonstrate

If the demo shows one thing, it is this: **the same vehicle, the same reviews, two different weighting strategies, different answers.**

```
   [ ✓ Equal ]  [ By source ]  [ By credibility ]        ← state 1

        Overall            8.3   [7.9 ─ 8.7]
        Service            7.1   [6.4 ─ 7.8]
        Gearbox            7.4   [6.9 ─ 7.9]

                    ↓  user clicks "By credibility"  ↓

   [ Equal ]  [ By source ]  [ ✓ By credibility ]        ← state 2

        Overall            7.8   [7.1 ─ 8.4]     ▼ 0.5
        Service            5.9   [5.1 ─ 6.6]     ▼ 1.2   ← the honest number
        Gearbox            6.2   [5.4 ─ 7.1]     ▼ 1.2
```

**What we say while showing it:** *"Same 412 reviews. On the left, every review counts once — which is what every review site does. On the right, reviews are weighted by how much they can be trusted, and long-term owners dominate. Service drops by 1.2 points. That gap is the product."*

For the wireframe demo this is **two drawings and a highlighted difference**. It must be prepared as a deliberate before-and-after pair, not improvised on the day.

---

## 8. Who does what

Roles follow the ownership areas agreed for the project, so that each person wireframes the surface they will later build.

| Owner | Screens | Also responsible for |
|---|---|---|
| **Saachi Shinde** — Application and Experience | **Verdict**, Landing / search, the variant picker | Design lead. Owns the shared conventions (spacing, typographic scale, how a score is always drawn) and assembles the final click-through. Runs the demo. |
| **Devika Jonjale** — Intelligence | **Evidence drawer**, Compare, Method | Owns the *content* of every number: that the aspects, ranges, divergence values and weight explanations are realistic and mean what the pipeline will actually produce. |
| **Aditya Nariyapara** — Platform and Ingestion | **Metrics**, Admin / source health | Owns realism of the placeholder data: plausible review counts per source, believable freshness and failure states, the two worked examples (one car, one two-wheeler). |

**Shared, and decided together on day one:** the screen map, the user flow, and the fidelity rules. Nobody draws in isolation before those three exist.

**Review rule.** Every screen is reviewed by at least one person who did not draw it, before the 7 August checkpoint. Fresh eyes catch the thing the author stopped seeing on day two.

---

## 9. Timeline, day by day

| Date | Day | What happens | Owner | Done when |
|---|---|---|---|---|
| **Fri 31 Jul** | — | Review 1. **Write down every piece of mentor feedback the same day.** | All | Feedback is captured in writing, not memory |
| Sat 1 – Sun 2 Aug | Weekend | Each person collects 5 reference screens they find genuinely clear — from any product, not just car sites — and one they find confusing | All | 18 references shared |
| **Mon 3 Aug** | 1 | **Kickoff, together.** Lock the tool. Agree the screen map, user flow and fidelity rules. Write the content rules: what a score looks like, what a range looks like, how a source is credited. | All | Screen map exists; tool decided |
| **Tue 4 Aug** | 2 | Low-fidelity sketches of **all seven screens**, fast and rough, in one sitting. Argue about layout now. | All | Every screen exists as a rough drawing |
| **Wed 5 Aug** | 3 | Verdict screen to mid fidelity. This is the day that matters most. | Saachi | Verdict screen readable and complete |
| **Thu 6 Aug** | 4 | Evidence drawer and Compare to mid fidelity | Devika | Both screens readable and complete |
| **Fri 7 Aug** | 5 | **Internal checkpoint.** All seven screens exist at some fidelity. Cross-review. Apply the cut rule if behind. | All | Go / no-go recorded, cuts decided |
| Sat 8 – Sun 9 Aug | Weekend | Buffer. Deliberately unscheduled. | — | — |
| **Mon 10 Aug** | 6 | Landing, Metrics, Method, Admin to mid fidelity | Aditya + Saachi | Four screens complete |
| **Tue 11 Aug** | 7 | Wire the click-through flow. Build the **weighting toggle before-and-after pair**. | Saachi | A viewer can click from search to verdict to evidence unaided |
| **Wed 12 Aug** | 8 | Consistency pass — every score drawn the same way everywhere. Realistic placeholder content for both worked examples. Write every annotation. | All | No screen contradicts another |
| **Thu 13 Aug** | 9 | **Freeze.** No new screens. Rehearse the walkthrough twice, out loud, timed. Export PNG/PDF and commit to `docs/wireframes/`. | All | Two clean rehearsals under six minutes; exports committed |
| **Fri 14 Aug** | 10 | **Milestone 2 demo.** | Saachi presents, all answer | — |

**Three rules that protect this timeline**

1. **The tool decision is made on 3 August and never revisited.** Changing tools mid-milestone costs three days.
2. **13 August is a freeze, not a work day.** A rehearsed demo of eighty percent beats an unrehearsed demo of a hundred.
3. **The weekend of 8–9 August is buffer, not planned work.** If we use it, we were behind. If we do not, we were on track.

---

## 10. How we will work

### 10.1 The tool

**Not yet decided.** The decision is due on Monday 3 August and belongs to the whole team. What matters is not which tool, but that it can do these four things:

| Requirement | Why |
|---|---|
| Three people can work on the same file | Otherwise we spend the milestone merging drawings |
| Screens can be linked so a viewer can click between them | A slideshow does not demonstrate a flow |
| It can export static images | So the work is committed to the repository and survives independently of any account |
| It is free for students | Consistent with everything else in this project |

Whatever we pick, the **exported images are the deliverable of record** and live in `docs/wireframes/`. A link to a design file is a convenience, not a submission.

### 10.2 Content rules, agreed on day one

Small and boring, and they are what stops seven screens from looking like three different products.

| Rule | Example |
|---|---|
| A score is always written the same way | `7.8 / 10` — never `78%`, never `3.9 stars` |
| A range is always shown, never a bare score | `7.8 [7.1 – 8.4]` |
| Evidence count always accompanies a score | `412 reviews · 6 sources` |
| Variants are always named in full | "Creta SX (O) 1.5 Diesel AT", never "Creta" |
| Every source is credited by name where its content appears | "CarDekho", with an outbound link |
| Placeholder numbers must be plausible | A variant with 12,000 owner reviews is not believable and will be the first thing our mentor questions |
| Dates are real and relative | "updated 2 days ago" |

### 10.3 Where things live

| Item | Location |
|---|---|
| This plan | `docs/review-1/02-milestone-2-wireframe-demo.md` |
| Exported wireframes | `docs/wireframes/` |
| Walkthrough script | `docs/wireframes/walkthrough.md` |
| Mentor feedback from Review 1 and Milestone 2 | `docs/wireframes/feedback.md` |

---

## 11. Definition of done

Milestone 2 is complete when every box is ticked. Not before, and nothing beyond it counts.

- [ ] All four **Must** screens exist at mid fidelity
- [ ] The three **Should** screens exist at least as clean sketches
- [ ] A viewer can click from search → verdict → evidence drawer without being guided
- [ ] The weighting toggle exists as a before-and-after pair with the changes marked
- [ ] Every number on every screen has an annotation saying where it will come from
- [ ] Both worked examples are drawn — one car, one two-wheeler
- [ ] The thin-evidence state is drawn, not just described
- [ ] A dead source is visible on the Admin screen
- [ ] Scores, ranges and evidence counts are drawn identically on every screen
- [ ] Exports are committed to `docs/wireframes/`
- [ ] The walkthrough has been rehearsed twice, timed, under six minutes
- [ ] Every screen has been reviewed by someone who did not draw it

---

## 12. The demo itself

Six minutes. Rehearsed. In this order.

| # | What we show | What we are saying |
|---|---|---|
| 1 | The search box, then a variant picker with 14 variants | "This is why variant-level matching is the hard problem" |
| 2 | The verdict screen, top section | "A score, an honest range, and the evidence base — stated, not hidden" |
| 3 | The topic cards | "Ordered by disagreement, not by score. This is the opposite of every competitor and it is deliberate" |
| 4 | The gearbox card's explanation line | "We do not just say people disagree. We say what explains it" |
| 5 | **Flip the weighting toggle** | "Same reviews. Service drops 1.2 points when we weight by trust. **That gap is the product**" |
| 6 | Click a number, open the evidence drawer | "Every number opens the reviews behind it, with the weight each one carried" |
| 7 | Compare, with two overlapping ranges | "These two are not distinguishable on this aspect. No comparison site will ever tell you that" |
| 8 | Admin, with one source failing | "A dead source degrades the product. It never breaks it" |
| 9 | The screen map | "And here is how all of it fits together" |

**Step 5 is the milestone.** If we run out of time, we skip steps 7 to 9, never step 5.

**What we will ask our mentor for, explicitly:**

1. Is the verdict screen readable at a glance, or is it too dense?
2. Is "divergence 0.61" meaningful to a normal buyer, or does it need different words?
3. Is the weighting switch understandable without us standing there explaining it?
4. What is missing that a real buyer would look for first?

---

## 13. Risks

| Risk | How likely | What we do about it |
|---|---|---|
| **The verdict screen is too dense.** It carries scores, ranges, divergence, splits, a media/owner comparison and the official record. | High | Draw a deliberately reduced version alongside the full one, and let the mentor choose on 14 August. Better to arrive with the question answered two ways than to defend one. |
| Tool churn — we start in one tool and switch | Medium | Decision locked 3 August, never revisited |
| Polishing instead of finishing — mid fidelity quietly becoming high fidelity | Medium | The 7 August checkpoint asks "does every screen exist?", not "is any screen beautiful?" |
| Three people drawing in three different styles | Medium | Content rules and shared conventions agreed on day one, plus the consistency pass on 12 August |
| Placeholder numbers that are not believable | Medium | Aditya owns data realism; every number is sanity-checked against what the real sources actually carry |
| Designing screens for data the pipeline will never produce | Low but expensive | Devika reviews every screen against the data model before the checkpoint |
| Demo runs long or rambles | Medium | Freeze on 13 August; two timed rehearsals; a fixed order with pre-agreed drop points |

---

## 14. Decisions we still have to make

| # | Decision | Owner | Due |
|---|---|---|---|
| 1 | Which wireframe tool | All three | Mon 3 Aug |
| 2 | Which two vehicles are our worked examples — one car, one two-wheeler | Aditya | Mon 3 Aug |
| 3 | What we call "divergence" on screen for a normal buyer — "disagreement"? "opinion split"? | Devika | Tue 4 Aug |
| 4 | Whether the evidence drawer slides over the page or opens a new one | Saachi | Wed 5 Aug |
| 5 | Whether the full or the reduced verdict layout becomes the default | Mentor, on 14 Aug | Fri 14 Aug |

---

**After this milestone.** The screens agreed here become the API contract and the page structure for the build, which starts the week of 17 August. Twelve-week plan in [docs/proposal.md](../proposal.md), section 24.
