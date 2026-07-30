# Review 1 — Concept, Market Gap and Literature Review

**Revix** · *driven by reviews.*
An evidence-traceable consumer decision support platform for the Indian automobile market.

| | |
|---|---|
| **Review** | Review 1 — idea, business need and background study |
| **Subject** | Modern Application Development |
| **Programme** | M.Sc. Data Science, Nilkamal School of Mathematics, Applied Statistics and Analytics, SVKM's NMIMS Mumbai |
| **Team** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |
| **Date** | 31 July 2026 |
| **Full design document** | [docs/proposal.md](../proposal.md) |

---

## Contents

1. [The idea, in one page](#1-the-idea-in-one-page)
2. [What the product actually means](#2-what-the-product-actually-means)
3. [Why this domain, and why India](#3-why-this-domain-and-why-india)
4. [Market gap analysis](#4-market-gap-analysis)
5. [Literature review](#5-literature-review)
6. [Where Revix sits, and what we are claiming](#6-where-revix-sits-and-what-we-are-claiming)
7. [Scope](#7-scope)
8. [Expected outcome](#8-expected-outcome)
9. [Questions we expect, and our answers](#9-questions-we-expect-and-our-answers)
10. [The ask](#10-the-ask)

---

## 1. The idea, in one page

### 1.1 The situation we are designing for

A person buying a vehicle in India today does roughly this:

| Step | What they read | What they come away with |
|---|---|---|
| 1 | Owner reviews on CarDekho | A 4.3-star average over 800 reviews |
| 2 | The same vehicle on CarWale or BikeWale | A 4.1-star average over a different 600 reviews |
| 3 | A forty-page Team-BHP ownership thread | Three genuinely useful posts, buried |
| 4 | Three YouTube reviews | Enthusiasm, filmed on a manufacturer-lent vehicle |
| 5 | A road test in Autocar India | A professional verdict on a pre-production car |

They finish with **six opinions that disagree with one another and no way to judge which of them deserves to be believed.**

Worse, the disagreement is *systematic*, not random:

- **Early reviews are kinder than late ones.** The people who write in the first three months are the people who just chose to buy the vehicle.
- **Media is kinder than owners.** Media drives the car for a weekend. Owners live with the service centre for five years.
- **Nobody surfaces the disagreement**, because a page that says "opinion is split" converts worse than a page that says 4.3 stars.

### 1.2 What Revix does about it

| COLLECT | MATCH | SCORE | COMBINE | EXPLAIN |
|---|---|---|---|---|
| Owner reviews, expert reviews, forums, videos, official records | Everything mapped to one exact vehicle variant | Opinion split topic by topic; each review scored for how much it can be trusted | Weighted into one verdict with a confidence range | Every number linked back to the reviews behind it |

Everything expensive runs **overnight in the background**, so the application itself is instant.

### 1.3 A worked example

This is what a user would see. Figures are illustrative.

```
 Hyundai Creta SX (O) 1.5 Diesel AT                        Rs 19.2L - 20.4L

 7.8 / 10  ████████████░░░░       confident between 7.1 and 8.4
 412 reviews · 6 sources · updated 2 days ago

 Weighting:  [ Equal ]  [ By source ]  [ ✓ By credibility ]   <- the flagship control

 MOST DISAGREEMENT
 Gearbox and transmission   6.2   [5.4 - 7.1]     divergence 0.61
 71% of the split is explained by transmission type.
 Automatic owners rate it 6.2 · manual owners rate it 8.8    [ 34 reviews ]

 Ride and comfort           8.6   [8.2 - 8.9]     divergence 0.12
 Service and after-sales    5.9   [5.1 - 6.6]     divergence 0.44
 Real-world mileage        17.2 kmpl   claimed 21.4 kmpl   ( -19.6% )

 EXPERT vs OWNER    media 8.9 ████████████████░░   owners 7.4 █████████████░░░░░
 Widest gap: service and after-sales (media 8.5, owners 5.9)

 OFFICIAL RECORD    Bharat NCAP 5-star adult / 4-star child · 1 recall (2024, fuel pump)
```

**Read that screen line by line and the whole idea is visible:**

| What you see | What it means |
|---|---|
| `7.8 / 10` with `[7.1 – 8.4]` | Not a star average. A weighted estimate **with an honest range around it.** |
| `412 reviews · 6 sources` | The evidence base is stated, not hidden. |
| The weighting switch | Flip it and every number on the screen moves. That is the intellectual content of the project, made visible. |
| Gearbox card **first**, at 6.2 | Cards are ordered by **disagreement**, not by score. The most contested topic is the most useful one. |
| "71% of the split is explained by transmission type" | We do not just say people disagree. We say **why**, using statistics, not guesswork. |
| Automatic 6.2 vs manual 8.8 | The single most useful sentence on the page for a buyer choosing a variant. |
| `17.2 kmpl vs claimed 21.4` | The claimed-versus-real gap, shown for every vehicle. No consumer product in India does this today. |
| Any number, clicked | Opens the exact reviews that produced it, with their weights. |

---

## 2. What the product actually means

### 2.1 It is a review *system*, not a review *summariser*

This distinction is the entire project, so it is worth stating carefully.

| A review summariser | Revix |
|---|---|
| Reads reviews **on one platform** | Reads **across** platforms and joins them |
| Averages the stars | **Weighs** each review by how much it can be trusted |
| Produces a paragraph of text | Produces a **structured verdict** — scores, ranges, splits — and then optionally writes prose about it |
| Says "the car is good" | Says "7.8, confident between 7.1 and 8.4, based on 412 reviews from 6 sources" |
| Sources are decorative, if present | Every number is **linked to its evidence in the database**, not by asking an AI to please cite things |
| Breaks if the AI is down | Renders the complete verdict **with the AI switched off entirely** |

### 2.2 The three things that make it different

**One — it reads across platforms instead of inside one.**
CarDekho can only tell you what CarDekho users think. No existing product joins CarDekho, CarWale, Team-BHP, YouTube and Bharat NCAP into a single judgement about a single vehicle variant.

**Two — it weighs reviews by trust instead of averaging stars.**
An owner who has driven 60,000 km over three years is a better witness to reliability than someone who posted on delivery day. An owner at 500 km is a better witness to the showroom experience. Indian review platforms record ownership duration and kilometres driven — and then throw that information away by averaging everything equally. We use it.

**Three — traceability is a property of the database, not a promise.**
When Revix says a vehicle scores 5.9 on service, there are rows in a table linking that claim to the specific reviews that produced it, each with the weight it contributed. Clicking the number opens them. This cannot silently break, because the number is computed *from* those links.

### 2.3 Why this is worth a semester

Because the honest version of this problem is genuinely hard, and every part of it is measurable:

| Sub-problem | Why it is hard | How we know if we did it well |
|---|---|---|
| **Identity** — is "Creta SX (O) 1.5 diesel AT" the same vehicle as "Creta 1.5 CRDi SX Optional Automatic"? | Every source names variants differently, and getting it wrong pollutes every downstream number | Precision, recall and F1 against a hand-labelled set of ~400 pairs |
| **Structure** — turning free text into comparable opinion, topic by topic | Reviews are unstructured, code-mixed Hinglish, and about nine different things at once | Macro-F1 against ~500 hand-labelled sentences, reported separately per language |
| **Trust** — which reviews deserve weight | There is no label for "this review is honest" | A held-out experiment: does credibility weighting predict long-term-owner consensus better than equal weighting? |
| **Accountability** — saying how sure we are, and why | Confidence is easy to fake and hard to earn | Calibration: does our 80% interval actually contain the truth 80% of the time? |

---

## 3. Why this domain, and why India

| Reason | Detail |
|---|---|
| **Small enough to finish** | A few hundred variants cover most of the market. The whole corpus can be precomputed overnight, which makes the application fast and cheap *by design*, not by optimisation. |
| **Matching is a real problem with a real solution** | Model names are almost a primary key. **Variant** names are genuinely messy. Hard enough to be interesting, bounded enough to finish in twelve weeks. |
| **Spec sheets are public** | So we can check claims in reviews against facts. A review claiming 21 kmpl can be compared against the ARAI figure. |
| **Reviews carry ownership metadata** | How long they kept it, how far they drove it. This is what makes trust-weighting possible at all, and it does not exist in most other review domains. |
| **Official data exists and is free** | Bharat NCAP crash ratings, SIAM recall notices, ARAI mileage figures, resale values. Nobody joins these to reviews. |
| **Two-wheelers are the bigger, worse-served half** | They are the large majority of Indian vehicle sales by volume, and get a fraction of the review infrastructure cars get. Same engine, double the audience. |
| **The things that decide Indian ownership are invisible today** | Service cost, spare-part availability and real-world mileage decide satisfaction here — and appear on no spec sheet and in no star rating. |

*Market-share figures to be cited from SIAM and the Vahan dashboard in the final report.*

---

## 4. Market gap analysis

### 4.1 What exists today, and where each one stops

Everything in this table is a real product a buyer can use right now. This is not a strawman comparison.

| Who | Genuinely good at | Where it stops |
|---|---|---|
| **CarDekho, CarWale, BikeWale, ZigWheels** | Huge volume of Indian owner opinion | Own platform only. One star average. Paid dealer leads, so ranking is not neutral. Fake and paid reviews are not filtered. |
| **Team-BHP, xBhp** | Genuinely excellent long-term ownership writing | Unstructured and unsearchable at scale. Nothing is aggregated. Heavily enthusiast-skewed. |
| **YouTube reviewers** | Detailed, visual, and popular | Manufacturer-lent vehicles, frequent sponsorship, no long-term view, and nobody is ever held to a claim. |
| **Autocar India, Overdrive** | Professional, repeatable testing methodology | Pre-production cars, short exposure, narrow catalogue, no owner voice. |
| **ChatGPT, Gemini, Perplexity** | Instant answer on anything | No credibility model, no verifiable sources, no stated confidence, and a different answer every time you ask. |
| **Fakespot, ReviewMeta** | Flagged fake reviews | **Both are shut down.** The category is empty right now. |
| **Bharat NCAP, SIAM recall portal** | Official, objective, free | Scattered across sites, hard to find, and joined to consumer reviews by nobody. |

### 4.2 The capability matrix

Read down the last column. That is the product.

| Capability | Portals | Forums | Video / Expert | AI chatbots | **Revix** |
|---|---|---|---|---|---|
| Reads across platforms, not just one | No | No | No | Some | **Yes** |
| Cars and two-wheelers in one system | Some | Some | Some | Some | **Yes** |
| Works at exact variant level | Some | No | No | No | **Yes** |
| Weighs reviews by trust | No | No | No | No | **Yes** |
| Filters fake or paid reviews | No | No | No | No | **Yes** |
| Verdict split topic by topic | No | Some | Some | Some | **Yes** |
| Shows where opinion splits, **and why** | No | No | No | No | **Yes** |
| States its own confidence | No | No | No | No | **Yes** |
| Every number traced to its reviews | No | No | No | No | **Yes** |
| Joined to recalls, safety and mileage claims | No | Some | No | No | **Yes** |
| Owner opinion shown against media opinion | No | Some | No | No | **Yes** |
| No paid ranking | No | Yes | Some | Some | **Yes** |

*"Some" means part of that category does it, or does it badly.*

### 4.3 Why these gaps survive — the part that matters

A gap that has stayed open for a decade usually stays open for a reason. Ours has three, and none of them is "nobody thought of it".

| Reason | Explanation |
|---|---|
| **Incentive.** The people who could close the gap are paid not to. | Portals earn from dealer leads and manufacturer advertising. A neutral ranking that says "the service experience on this car is poor" costs them revenue directly. They will never build it. This is structural, not lazy. |
| **Disagreement looks like a defect.** | A product page that admits opinion is split converts worse than one showing 4.3 stars. Every commercial incentive pushes towards a single confident number, which is exactly the number that is least useful to a buyer. |
| **Cross-platform aggregation has no business model.** | Fakespot and ReviewMeta both tried adjacent versions of this and are both gone. The work is real, the running costs are real, and there is no obvious way to monetise it without recreating the bias you set out to remove. |

**This is what makes the gap worth building into for an academic project specifically.** We have no revenue to protect. We can show the disagreement, state our uncertainty, and refuse to rank by who pays — none of which a commercial player can afford to do.

### 4.4 The gap, stated in one sentence

> **Every existing system either aggregates within one platform's walls, or reasons without traceability — and none of them joins consumer review evidence to the objective public record.**

---

## 5. Literature review

### 5.1 How we read the literature

Revix is not one research problem. It is six well-studied problems that nobody has assembled in this order. So the review is organised by **theme**, and each theme answers three questions:

- What does the literature establish?
- What do we take from it?
- What does it *not* answer for our setting?

### 5.2 Theme A — Online reviews are systematically biased

| | |
|---|---|
| **What is established** | Review distributions are famously **J-shaped**: mostly five stars, some one star, very little in between. This is a *self-selection* effect — people with extreme experiences write reviews (Hu, Pavlou & Zhang, 2009). Opinion also **drifts over time**, with early reviews systematically more positive than later ones (Godes & Silva, 2012; Moe & Schweidel, 2012). Review helpfulness is itself predictable from review characteristics, and depends on the product type (Mudambi & Schuff, 2010). |
| **What we take** | Averaging stars is not a neutral operation — it *encodes* the bias. This directly justifies two of our design decisions: the **launch-window correction** in the weighting function, and reporting a **distribution and divergence** instead of a mean. |
| **What is still open for us** | This literature describes bias; it does not tell you which individual reviews to trust more. That is theme C. And almost none of it is on Indian automotive data. |

### 5.3 Theme B — Fake, paid and deceptive reviews

| | |
|---|---|
| **What is established** | Opinion spam was formalised by Jindal & Liu (2008). Ott et al. (2011) showed that deceptive reviews are detectable from text alone at well above human accuracy, using crowdsourced deceptive reviews as a training set. Mukherjee et al. (2013) showed that **behavioural** signals — posting bursts, reviewer history, rating deviation — matter as much as text. Luca & Zervas (2016) showed with Yelp data that review fraud is an economically rational response to competition, i.e. it is not rare and it is not going away. |
| **What we take** | A supervised spam classifier is a solved-enough problem to be a *component* rather than a research contribution, and it should combine textual and behavioural features. We use it as **one multiplier** in the weighting function, not as a binary filter. |
| **What is still open for us** | Public labelled deceptive-review corpora are English, and mostly hotels and restaurants. Transferring to Hinglish automobile reviews is untested, which is a real risk we report rather than hide. |

### 5.4 Theme C — From "is this fake?" to "how much should this count?"

| | |
|---|---|
| **What is established** | The **truth discovery** literature addresses exactly our shape of problem: many sources make conflicting claims about the same objects, and source reliability must be inferred *jointly* with the truth, without ground truth. TruthFinder (Yin, Han & Yu, 2008) established the iterative formulation; Dong et al. (2009) added source dependence (sources copying each other); Li et al. (2016) survey the field. |
| **What we take** | The core insight — that **source trust and the truth are estimated together** — is the intellectual ancestor of our credibility weighting. |
| **What is still open for us** | This literature almost always assumes *factual* claims with a single correct answer ("what is this book's ISBN?"). Ours are **subjective judgements where disagreement can be legitimate** — an automatic gearbox genuinely is worse in traffic and fine on a highway. Classical truth discovery would treat that as one source being wrong. **Our covariate attribution is the response to that gap, and it is the most defensible original element of the design.** |

### 5.5 Theme D — Entity resolution

| | |
|---|---|
| **What is established** | Record linkage has a formal foundation going back to Fellegi & Sunter (1969). Modern approaches use deep learning (Mudgal et al., 2018) and pre-trained language models (Ditto; Li et al., 2020), and consistently show that **blocking** plus a learned matcher beats either alone. |
| **What we take** | The standard pipeline shape: block, then constrain, then match, then verify. |
| **What is still open for us** | The literature's benchmark datasets rarely have **hard physical constraints**. We do: a petrol listing is never a diesel variant, whatever the embeddings say. Exploiting spec fields as hard constraints before any learned matching is what lets us aim for very high precision on a small budget, and it is a domain advantage the general literature cannot use. |

### 5.6 Theme E — Aspect-based sentiment analysis

| | |
|---|---|
| **What is established** | ABSA is a mature task with standard benchmarks and shared tasks (Pontiki et al., SemEval-2014 Task 4 and successors), covering aspect extraction, aspect-category detection and polarity classification. Sentence embeddings (Reimers & Gurevych, 2019) made semantic similarity cheap enough to use at scale. |
| **What we take** | A **fixed nine-aspect taxonomy** rather than open aspect extraction, because a fixed taxonomy is comparable across vehicles and measurable against a gold set. Bootstrap the labels with an LLM, correct them by hand, then distil into a cheap classifier for batch inference. |
| **What is still open for us** | Two of our nine aspects — **service and after-sales**, and **long-term reliability** — barely appear in the benchmark taxonomies, because those benchmarks are restaurants and laptops. These two dominate Indian vehicle ownership. Building and measuring them is our own work. |

### 5.7 Theme F — Uncertainty and calibration

| | |
|---|---|
| **What is established** | Weighted survey estimates have a well-defined **effective sample size**, `n_eff = (Σw)² / Σw²` (Kish, 1965) — a standard result from survey sampling. Separately, modern ML models are known to be **badly calibrated** by default, and calibration is measurable with reliability diagrams and expected calibration error (Guo et al., 2017). |
| **What we take** | Both, almost directly. Kish's quantity is one line of code and it captures something genuinely important: 200 low-credibility reviews can carry a *smaller* effective sample than 30 high-credibility ones, so the confidence interval correctly stays wide. Calibration measurement is what turns our confidence meter from decoration into an evidenced claim. |
| **What is still open for us** | Nothing conceptually. This is a case of importing a mature idea into a place nobody has bothered to put it. That is a legitimate engineering contribution, and we will present it as exactly that. |

### 5.8 Theme G — Grounding, attribution and hallucination

| | |
|---|---|
| **What is established** | Retrieval-augmented generation (Lewis et al., 2020) is the dominant pattern for grounding language models in sources. Hallucination is well surveyed (Ji et al., 2023). Critically, **attribution is measurable**: Rashkin et al. (2023) formalise whether a generated statement is actually supported by its cited source, and the consistent finding is that models cite unreliably when asked to cite. |
| **What we take** | The lesson, not the architecture. Since asking a model to cite produces unreliable citations, **we never ask it to.** The citation links are produced by our fusion engine and stored as rows *before* any text is generated. The model receives only opaque claim identifiers and never sees raw review text. A deterministic validator then checks that every number in the generated prose was actually computed, and falls back to a template if not. |
| **What is still open for us** | Most of this literature optimises *how well the model cites*. We sidestep the question by making citation structural. **This is our clearest departure from the standard pattern, and the reason our verdict still renders with the language model switched off.** |

### 5.9 Theme H — Code-mixed and Hinglish text

| | |
|---|---|
| **What is established** | Code-switched NLP is a recognised hard case with its own benchmarks (GLUECoS; Khanuja et al., 2020) and dedicated Hindi–English resources and models (L3Cube HingCorpus and HingBERT; Nayak & Joshi, 2022). Multilingual sentence embeddings can be produced by distillation from an English model (Reimers & Gurevych, 2020). |
| **What we take** | Use a multilingual encoder rather than an English-only one, preprocess tolerantly for transliteration, detect and store the language on every review, and **report accuracy separately per language.** |
| **What is still open for us** | Performance on transliterated Hinglish automotive text is genuinely unknown. We treat this as a measured, reported number rather than an assumption — being transparent about degraded Hinglish accuracy is more credible than concealing it. |

### 5.10 What the literature does *not* give us

This is the honest summary, and the part worth saying out loud in the review.

| Every piece exists | But | Nobody has |
|---|---|---|
| Spam detection is solved-enough | it is used as a filter, not as a weight | ...used credibility as a **continuous, aspect-conditional weight** |
| ABSA is mature | benchmarks are restaurants and laptops | ...built an aspect taxonomy around **Indian after-sales and long-term reliability** |
| Truth discovery infers source trust | it assumes one objectively correct answer | ...handled **legitimate** subjective disagreement, and explained it by covariate |
| Effective sample size is textbook survey statistics | it lives in survey methodology, not consumer products | ...used it to make a **consumer-facing confidence interval honest** |
| Attribution is measurable | it is measured *on the model's own citations* | ...made citation **structural**, so it cannot be wrong |

> **The contribution we claim is assembly, not invention.** Each component is defensible individually because it rests on established work. The combination does not exist as a product anywhere, in India or outside it.

### 5.11 References

*To be finalised in the department's citation style before final submission.*

1. Dong, X. L., Berti-Equille, L., & Srivastava, D. (2009). *Integrating conflicting data: the role of source dependence.* VLDB.
2. Fellegi, I. P., & Sunter, A. B. (1969). *A theory for record linkage.* Journal of the American Statistical Association.
3. Godes, D., & Silva, J. C. (2012). *Sequential and temporal dynamics of online opinion.* Marketing Science.
4. Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). *On calibration of modern neural networks.* ICML.
5. Hu, N., Pavlou, P. A., & Zhang, J. (2009). *Overcoming the J-shaped distribution of product reviews.* Communications of the ACM.
6. Ji, Z., et al. (2023). *Survey of hallucination in natural language generation.* ACM Computing Surveys.
7. Jindal, N., & Liu, B. (2008). *Opinion spam and analysis.* WSDM.
8. Khanuja, S., Dandapat, S., Srinivasan, A., Sitaram, S., & Choudhury, M. (2020). *GLUECoS: An evaluation benchmark for code-switched NLP.* ACL.
9. Kish, L. (1965). *Survey Sampling.* Wiley.
10. Lewis, P., et al. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks.* NeurIPS.
11. Li, Y., Gao, J., Meng, C., Li, Q., Su, L., Zhao, B., Fan, W., & Han, J. (2016). *A survey on truth discovery.* SIGKDD Explorations.
12. Li, Y., Li, J., Suhara, Y., Doan, A., & Tan, W.-C. (2020). *Deep entity matching with pre-trained language models (Ditto).* VLDB.
13. Luca, M., & Zervas, G. (2016). *Fake it till you make it: reputation, competition, and Yelp review fraud.* Management Science.
14. Moe, W. W., & Schweidel, D. A. (2012). *Online product opinions: incidence, evaluation, and evolution.* Marketing Science.
15. Mudambi, S. M., & Schuff, D. (2010). *What makes a helpful online review?* MIS Quarterly.
16. Mudgal, S., et al. (2018). *Deep learning for entity matching: a design space exploration.* SIGMOD.
17. Mukherjee, A., Venkataraman, V., Liu, B., & Glance, N. (2013). *What Yelp fake review filter might be doing?* ICWSM.
18. Nayak, R., & Joshi, R. (2022). *L3Cube-HingCorpus and HingBERT: Hindi-English code-mixed resources.* WILDRE / LREC workshop.
19. Ott, M., Choi, Y., Cardie, C., & Hancock, J. T. (2011). *Finding deceptive opinion spam by any stretch of the imagination.* ACL.
20. Pontiki, M., et al. (2014). *SemEval-2014 Task 4: Aspect based sentiment analysis.* SemEval.
21. Rashkin, H., et al. (2023). *Measuring attribution in natural language generation models.* Computational Linguistics.
22. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: sentence embeddings using Siamese BERT-networks.* EMNLP.
23. Reimers, N., & Gurevych, I. (2020). *Making monolingual sentence embeddings multilingual using knowledge distillation.* EMNLP.
24. Yin, X., Han, J., & Yu, P. S. (2008). *Truth discovery with multiple conflicting information providers on the web.* IEEE TKDE.

**Non-academic sources.** Bharat NCAP published crash ratings; SIAM voluntary recall portal; ARAI certified fuel-efficiency figures; SIAM and Vahan registration and sales data; published terms of service and `robots.txt` of every source we collect from.

---

## 6. Where Revix sits, and what we are claiming

### 6.1 The positioning

```
        aggregates across sources
                    ▲
                    │
      Revix ●       │
                    │
   ─────────────────┼─────────────────►  traceable to specific evidence
                    │
                    │   ● AI chatbots            ● Portals (CarDekho etc.)
                    │     (broad, untraceable)     (traceable, single-walled)
                    │
```

Portals are traceable but trapped inside one platform. Chatbots read broadly but cannot show you what they read. **Revix is the quadrant nobody occupies.**

### 6.2 What we claim, and what we do not

Stating this clearly protects us in the viva.

| We claim | We do **not** claim |
|---|---|
| A well-engineered system that does something no existing product does | A novel research contribution |
| Each component rests on established literature, correctly applied | A new algorithm or a state-of-the-art result |
| Every claim we make in the interface is traceable to specific evidence | That our verdict is objectively "correct" — there is no ground truth for consumer opinion |
| Our confidence intervals are **measured** for calibration, not asserted | Statistical guarantees beyond what our held-out experiment supports |
| Accuracy is reported honestly, including where it is poor | Absolute assertions about any manufacturer's quality |

**This is a Modern Application Development project.** The claim is a well-built, deployed, measured application with substantial and well-integrated machine learning — not a thesis.

---

## 7. Scope

| We are building | We are not building |
|---|---|
| Indian cars **and two-wheelers** | Commercial vehicles |
| ~120 to 150 popular variants, seeded deliberately | Arbitrary vehicles outside our catalogue |
| Six to eight sources | Live scraping on every request |
| Verdict, compare, evidence, method, metrics and admin screens | Booking or dealer integration |
| Measured accuracy for every component we build | User accounts, mobile apps, used-vehicle pricing |

**How we collect responsibly.** Rate-limited and cached. Attributed and linked back. We store references and derived structure, **not mirrored copies** of anyone's content. Author identities are pseudonymous, never personal data. Official APIs are used wherever one exists. If a source's terms forbid what we want to do, we drop that source — and the system is designed to stay complete with only three of eight sources alive.

---

## 8. Expected outcome

| # | Deliverable |
|---|---|
| 1 | A **live, publicly reachable web application** for Indian cars and two-wheelers |
| 2 | A **vehicle catalogue at variant level**, with matching accuracy reported honestly |
| 3 | A **collection pipeline** across six to eight sources, with a live health dashboard |
| 4 | The **trust-weighting engine**, switchable inside the application while you watch |
| 5 | **Every number traceable** to the reviews behind it, by clicking it |
| 6 | A **public code repository**, a written report, and a rehearsed six-minute demo |

---

## 9. Questions we expect, and our answers

Prepared in advance, because these are the obvious ones.

| Question | Our answer |
|---|---|
| **"Isn't this just a ChatGPT wrapper?"** | No. The verdict is computed by a statistical pipeline and stored in a database. A language model only writes the final sentences, and **the application renders a complete verdict with the model switched off.** We will demonstrate exactly that. |
| **"How do you know your verdict is right?"** | We don't, and we do not claim to — there is no ground truth for consumer opinion. What we *can* test is whether trust-weighting beats star-averaging: we hold out long-term verified owners as a target, estimate it from the remaining mixed-quality reviews, and compare weighting strategies. That is measurable and non-circular. |
| **"Is scraping these sites legal?"** | We read `robots.txt` and terms before writing each connector and record what they say. We rate-limit, cache, attribute and link back, and store references rather than copies. Where an official API exists we use it. Where terms forbid it, we drop the source. |
| **"Is this too much for three people in twelve weeks?"** | It is deliberately bounded: a fixed catalogue, one database, no live inference, and a hard cut list agreed in advance with checkpoints at weeks 4 and 8. The system is designed to remain complete and demonstrable with only three of eight sources working. |
| **"What if a site blocks you?"** | Each source is an isolated connector with a documented fallback dataset. One dying degrades coverage; it never breaks the product. |
| **"Where is the machine learning?"** | Seven components: entity resolution, aspect extraction, spam detection, reliability weighting, divergence analysis, claim verification and grounded narration. Each has its own measured metric on a public metrics page. |
| **"What is genuinely new here?"** | Assembly, not invention — and we say so. The pieces are established; nobody has combined them into a consumer product, and the *reason* nobody has is commercial, not technical. |
| **"Why include two-wheelers?"** | They are the larger and worse-served half of the Indian market, and they cost almost nothing architecturally — a motorcycle is a catalogue row with a different spec profile. The catalogue budget is **split, not increased.** |

---

## 10. The ask

> **Approval to proceed on this scope:** Indian cars and two-wheelers, with the trust-weighted, fully traceable review verdict as the core of the product.

**Next milestone:** Milestone 2 — Wireframe Demo, Friday 14 August 2026. Plan in [02-milestone-2-wireframe-demo.md](02-milestone-2-wireframe-demo.md).
