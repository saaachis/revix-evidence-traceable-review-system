# S1 — Business Need

**Revix** · *driven by reviews.*
An evidence-traceable consumer decision support platform for the Indian automobile market.

| | |
|---|---|
| **Submission** | S1 Business Need |
| **Subject** | Modern Application Development |
| **Programme** | M.Sc. Data Science, NMIMS Mumbai |
| **Team** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |

> A person buying a vehicle in India today reads owner reviews on CarDekho, then the same vehicle on CarWale or BikeWale, then a forty-page Team-BHP ownership thread, then three YouTube reviews, then a road test in Autocar India. They finish with six opinions that disagree with one another and no way to judge which of them deserves to be believed.
>
> **Revix reads all of them, works out which reviews deserve trust, and gives one clear verdict where every number links back to the reviews behind it.**

---

## 1. The problem

| Where people look today | What is wrong with it |
|---|---|
| CarDekho, CarWale, BikeWale | One star average. Fake and paid reviews never filtered. |
| Team-BHP, xBhp forums | Real depth, buried in 100-page threads. Nothing aggregated. |
| YouTube reviewers | Manufacturer-lent vehicles, often sponsored. No long-term view. |
| Autocar, Overdrive | Pre-production cars, short drives, narrow catalogue. |
| Bharat NCAP, recall portals | Official and free, but joined to reviews by nobody. |

The bias always runs one way. Early reviews are kinder than late ones. Media is kinder than owners. Nobody shows the disagreement, because disagreement makes a product page look bad.

## 2. What Revix does

| COLLECT | MATCH | SCORE | COMBINE | EXPLAIN |
|---|---|---|---|---|
| Owner reviews, expert reviews, forums, videos, official records | Everything mapped to one exact vehicle variant | Opinion split by topic; each review scored for trust | Weighted into a verdict with a confidence range | Every number linked to the reviews behind it |

*Runs every night in the background, so the app itself is instant.*

**It is a review system, not a review summariser.** Three differences:

- It reads **across** platforms instead of inside one.
- It **weighs** reviews by how much they can be trusted, instead of averaging stars.
- Every claim **links to its source reviews**, guaranteed by the database, not by asking an AI nicely.

## 3. Why cars and bikes, and why India

- **Small enough to finish.** A few hundred variants cover most of the market.
- **Matching is a real problem.** "Creta SX (O) 1.5 diesel AT" and "Creta 1.5 CRDi SX Optional Automatic" are the same car.
- **Spec sheets are public**, so we can check claims against facts.
- **Reviews say how long owners kept the vehicle and how far they drove it**, which tells us who is worth believing about what.
- **Official data exists**: Bharat NCAP, recall notices, ARAI mileage, resale prices.
- **Two-wheelers are the bigger, worse-served half.** Same engine, double the audience.
- **Service cost and real mileage** decide Indian ownership, and appear on no spec sheet or star rating.

## 4. The market gap

Everything below is a product a buyer can use today.

| Who | Good at | Where it stops |
|---|---|---|
| CarDekho, CarWale, BikeWale, ZigWheels | Huge review volume | Own platform only. Star average. Paid dealer leads, so ranking is not neutral. |
| Team-BHP, xBhp | Genuine long-term ownership | Unstructured, unsearchable, enthusiast-skewed. |
| YouTube reviewers | Detailed and visual | Press vehicles, sponsorship, nobody is held to a claim. |
| Autocar, Overdrive | Professional testing | Pre-production cars, narrow catalogue, no owner voice. |
| ChatGPT, Gemini, Perplexity | Instant answer on anything | No credibility model, no sources, no confidence, different answer each time. |
| Fakespot, ReviewMeta | Flagged fake reviews | Both shut down. The category is empty right now. |
| Bharat NCAP, SIAM recalls | Official and objective | Scattered, hard to find, never joined to reviews. |

*Table 1. Who exists, and where each one stops.*

| Capability | Portals | Forums | Video / Expert | AI chatbots | **Revix** |
|---|---|---|---|---|---|
| Reads across platforms, not just one | No | No | No | Some | **Yes** |
| Cars and bikes in one system | Some | Some | Some | Some | **Yes** |
| Works at exact variant level | Some | No | No | No | **Yes** |
| Weighs reviews by trust | No | No | No | No | **Yes** |
| Filters fake or paid reviews | No | No | No | No | **Yes** |
| Verdict split topic by topic | No | Some | Some | Some | **Yes** |
| Shows where opinion splits, and why | No | No | No | No | **Yes** |
| States its own confidence | No | No | No | No | **Yes** |
| Every number traced to its reviews | No | No | No | No | **Yes** |
| Joined to recalls, safety, mileage claims | No | Some | No | No | **Yes** |
| Owner opinion shown against media opinion | No | Some | No | No | **Yes** |
| No paid ranking | No | Yes | Some | Some | **Yes** |

*Table 2. The comparison that matters. "Some" means part of the category does it, or does it badly.*

**Why these gaps survive:** closing them costs the people who could close them. Portals earn from dealer leads, so they will never rank neutrally. That is what makes the gap worth building into.

## 5. How it is built

| | |
|---|---|
| **SCREENS** | Next.js, TypeScript, Tailwind |
| **API** | FastAPI, read-only, contract-first |
| **DATA** | One PostgreSQL database with pgvector. Not four separate services. |
| **PIPELINE** | Nightly batch: match → score → combine → explain |
| **SOURCES** | Independent connectors, one per site. Any of them can fail safely. |

*Machine learning: sentence-transformers and scikit-learn. An AI model writes the final sentences only, and the app works fully without it. Everything is free-tier.*

- **Fast.** Pages load in under a third of a second, because nothing is computed while you wait.
- **Fails safely.** Any source, or the AI itself, can go down and the verdict still shows.
- **Honest.** Every screen shows how many reviews it used and when it last refreshed.

## 6. What the user sees

```
 Hyundai Creta SX (O) 1.5 Diesel AT                        Rs 19.2L - 20.4L

 7.8 / 10  ████████████░░░░       confident between 7.1 and 8.4
 412 reviews · 6 sources · updated 2 days ago

 Weighting:  [ Equal ]  [ By source ]  [ ✓ By credibility ]   ← flagship control

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

*Rough sketch of the main screen. Topics are ordered by how much people disagree, not by score.*

- **The switch.** Flip between equal weighting and trust weighting and watch the scores move. This is the whole idea, made visible.
- **Click any number** to see the exact reviews behind it.
- **Ranges, not decimals.** If two vehicles overlap, we say so instead of pretending.
- **Claimed vs real mileage**, shown for every vehicle.

## 7. Risks, and what we do about them

| Risk | What we do |
|---|---|
| A site blocks us | Each source is separate with a backup dataset. The product still works with three of eight sources alive. |
| Terms of service | Rate-limited, cached, credited, linked back. We store links, not copies. |
| Hinglish review text | A multilingual model, and we report accuracy per language instead of hiding it. |
| Doing too much, three people | Hard checkpoints at week 4 and week 8, with a cut list agreed in advance. |

## 8. Scope

| WE ARE BUILDING | WE ARE NOT BUILDING |
|---|---|
| Indian cars and bikes · about 120 to 150 popular variants · six to eight sources · verdict, compare, evidence and admin screens · measured accuracy for everything we build | Commercial vehicles · used-vehicle pricing · live scraping per request · vehicles outside our list · booking or dealer integration · user accounts · mobile apps |

## 9. What we will hand over

- A **live web app** for Indian cars and bikes.
- A **vehicle catalogue** at variant level, with matching accuracy reported honestly.
- A **collection pipeline** across six to eight sources, with a health dashboard.
- The **trust-weighting engine**, switchable live inside the app.
- **Every number traceable** to the reviews behind it.
- A **public code repository**, a short report, and a rehearsed demo.

> **What we are asking for.** Approval to start on this scope: Indian cars and two-wheelers, with the trust-weighted review verdict as the core of the product.

---

*The full technical design behind this submission is in [proposal.md](proposal.md).*
