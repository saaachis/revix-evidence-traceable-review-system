# S3: Working Demo

**Revix** · *driven by reviews.*
The runbook: what to show, in what order, on what, and what to do when
something breaks.

| | |
|---|---|
| **Submission** | S3 Working demo |
| **Weight** | **20 marks** of 100 |
| **Due** | **Friday 16 October 2026** |
| **Marked on** | The application should work. A video may serve as backup |
| **Team** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |
| **Live site** | `https://revix-reviews.vercel.app` |
| **Live API** | `https://revix-api-tcyq.onrender.com` |
| **Companion** | [Speaking script](02-working-demo-speaking-script.md) |

> **Read the rubric literally.** The mark is for the application *working*, not
> for novelty. The demo is therefore built around one uninterrupted path that
> is guaranteed to work, with the interesting material offered as detours we
> can take if there is time. Never open with something that might fail.

---

## 1. The single most important decision

**Demo the deployed site, not localhost.** A live URL the examiner can open on
his own phone is worth more than anything running on your laptop, and it
removes "does it only work on your machine" as a question entirely.

**Record the backup video anyway.** The rubric explicitly permits it, which
means it is expected, and it costs one afternoon. See [§7](#7-the-backup-video).

---

## 2. Pre-flight, the morning of

Run through this list. It takes four minutes and it is the difference between
a demo and an incident.

| # | Check | Command or action | Expected |
|---|---|---|---|
| 1 | The API is awake and healthy | `curl -s $API/health` | `"status":"ok"`, `"database":true`, non-zero counts |
| 2 | All three sources are healthy | `curl -s $API/sources/health` | No source reporting `circuit_open` |
| 3 | The nightly run succeeded | GitHub Actions, latest nightly | Green |
| 4 | `main` is green | GitHub, CI checks | All six jobs pass |
| 5 | The site is warm | Load the home page **twice** | Second load is instant |
| 6 | Your demo variant still resolves | Open its verdict page directly | Loads, unsuppressed, has evidence |
| 7 | The comparison you plan to show still exists | Open `/compare` and click the pair | Both sides populated |
| 8 | Phone check | Open the site on a phone | Layout holds |

> **Warm the site fifteen minutes before, and again five minutes before.** The
> free tier idles the instance out. This single habit prevents the most likely
> failure of the day.

**Pick your demo variant the night before, not live.** Choose one with a high
evidence count and visible disagreement, since disagreement is what makes the
product's argument. Write the URL here before the demo:

```
Demo variant URL:  ______________________________________________
Backup variant URL: ______________________________________________
```

---

## 3. The demo flow

Ten minutes of screen time. Each step names what to click and what the
examiner should notice.

### Step 1: The home page (30 seconds)

**Show:** `https://revix-reviews.vercel.app`

State the problem in one sentence, then move. Do not linger on the landing
page; nothing is being marked here.

### Step 2: Browse the catalogue (1 minute)

**Click:** *Browse*

**What to point out:** the scale is real. **143 variants across 42 models and
16 manufacturers**, cars and two-wheelers, every one of them carrying a
verdict built from real reviews.

**Show the filters working**: vehicle class, and the free-text search. Type a
model name and let the list narrow. This proves the catalogue is queryable,
not a fixed list.

### Step 3: A verdict (2 minutes), **the core of the demo**

**Click:** into your chosen variant.

Three things to point at, in this order:

1. **The score has a range, not just a number.** That is a bootstrap
   confidence interval, and it is on screen because a single decimal would be
   a lie about precision.
2. **The evidence count and the effective sample size.** These are different
   numbers on purpose: the effective sample size accounts for how unevenly the
   reviews are distributed, so a verdict built from one very loud source is
   visibly weaker than one built from many.
3. **The aspects, ordered with the most-disagreed-upon at the top.**
   Disagreement is the useful signal, so it is what the layout leads with.

### Step 4: Traceability (2 minutes), **the differentiator**

**Click:** any score, to open its evidence.

> This is the claim the whole project rests on. Every number opens the actual
> sentences it was computed from, with the source, the link and the weight
> each one contributed.

**Point out that the citations are ranked by contribution weight**, and that
these rows were written by the fusion engine *before* any prose existed. The
score was computed *from* them, which is why the citation cannot be wrong. It
is not a language model asked to justify a number after the fact.

**Follow one link out to the original review** on CarWale or CarDekho, so he
sees a real page on a real site. Doing this once is worth a paragraph of
explanation.

### Step 5: The weighting switch (1.5 minutes), **the "wow" moment**

**Back on the verdict page, flip the weighting** between equal,
source-weighted and credibility-weighted.

> Watch the numbers move. That is the same evidence under three different
> trust models.

Then the line that matters:

> **This is instant because nothing is computed here.** All three verdicts
> were calculated by the pipeline overnight and stored. Switching is a lookup,
> not a recomputation. That is the same architectural decision that gives us
> our latency and our demo reliability.

### Step 6: Comparison (1 minute)

**Click:** *Compare*, pick a suggested pair.

Pairs are generated by taking one variant per model and pairing price
neighbours within a vehicle class, so the suggestions are vehicles a person
would actually cross-shop.

### Step 7: Honesty pages (1.5 minutes)

These carry more marks than they look like they do, because they answer "how
do we know any of this is true."

**Sources**: where every source stands, with unit counts and last success. A
dead source degrades the system; it does not break it.

**Status**: the pipeline's own health.

**Accuracy**: our published measurements, *including the unflattering one*.
The aspect classifier we built lost to the lexicon it was trained from and
ships disabled. **Show this deliberately.** A project that publishes the
result that went against it is making a stronger claim than one that only
publishes wins.

**Method**: how a verdict is built, in plain language.

### Step 8: Suppression (30 seconds)

**Show a variant held back below the evidence floor.**

> Nine of our 143 variants do not have enough evidence to say anything
> responsibly, so we say nothing and explain why, rather than showing a
> confident-looking number built from four reviews.

Refusing to answer is a feature. Make sure it is seen.

---

## 4. Optional detours, only if invited

Do not volunteer these. Have them ready if he asks for more.

| If he asks about | Show |
|---|---|
| Speed | Browser dev tools, network tab: the `X-Response-Time-ms` header on a response |
| Security | The response headers: CSP, HSTS, nosniff |
| Failure behaviour | `/health` and `/sources/health` returning real JSON |
| The API itself | `/docs`, the generated OpenAPI page |
| Accessibility | Tab through the verdict page with the keyboard only |
| Mobile | Hand him your phone with the site already open |

---

## 5. What can break, and what to say

| Failure | Say this | Then do this |
|---|---|---|
| Site is slow to first load | "That is the free-tier cold start; the instance idles out and we ping it on a schedule to reduce it" | Keep talking, it wakes |
| A page errors | "That is our error boundary rather than a blank page" | Reload; move to the next step |
| API is down entirely | "This is why we brought the video" | Switch to the recording without ceremony |
| A source shows `circuit_open` | "A source failed and the site kept serving; the status page shows it" | Open `/sources` and **turn it into the reliability point** |
| Data looks different from this document | "The pipeline ran last night, so the numbers move" | Read the live numbers off the screen |
| Something genuinely is broken | "That is a real bug, and here is what I think it is" | Diagnose honestly. Do not pretend it is intended |

> **The rule: never say "it usually works."** Either show it, or say plainly
> that it is broken and what you would check first. A calm diagnosis reads
> better than a flustered excuse, and this examiner will have seen a hundred
> flustered excuses.

---

## 6. Equipment

| | |
|---|---|
| Laptop, charged, charger present | |
| Browser: one window, demo tabs only | Close everything else, including notifications |
| Zoom level ~110% so text is readable on a projector | |
| Phone with the site loaded, for the responsive check | |
| Backup video on the laptop **and** on a phone or drive | Not only in the cloud |
| This runbook, printed or on a second device | Not on the screen you are sharing |
| Hotspot ready, in case the room's network fails | |

---

## 7. The backup video

Record it **a week before**, not the night before, so there is time to redo it.

| | |
|---|---|
| **Length** | 5 to 6 minutes |
| **Content** | Steps 1 to 8 of §3, in order, no detours |
| **Audio** | Narrated. A silent screen recording does not carry the argument |
| **Quality** | 1080p, cursor visible, no notifications on screen |
| **Store** | On the laptop, on a drive, and uploaded. Test playback on the laptop you will bring |
| **Name** | `revix-working-demo-<date>.mp4` |

Record it in one take if you can. A video with one small stumble looks like
software; a heavily edited one looks like a trailer.

---

## 8. Rehearsal

Rehearse the full flow **at least twice**, once end to end without stopping,
and once with someone interrupting to ask questions. Time it. If it runs past
twelve minutes, cut step 6 rather than rushing step 4, because traceability is
the mark and comparison is a nicety.

Rehearse **on the room's setup if you can get in beforehand**, or at least on
an external display, since projector colour and text size are the two things
that surprise people.

---

## 9. Refreshing the numbers in this document

```bash
API=https://revix-api-tcyq.onrender.com
curl -s $API/health
curl -s $API/sources/health
curl -s "$API/variants?limit=200" | python -c "import sys,json; d=json.load(sys.stdin); print(len(d),'variants,',sum(1 for v in d if not v['is_suppressed']),'published')"
```

Figures quoted here were taken on **7 September 2026** and will have grown.
Read the live ones off the screen during the demo rather than quoting this
page.
