# Assignment 1 report

FRE-GY 7871 A · NLP and the Investment Process

**Name:**
**NetID:**
**GitHub repo:**

Target length 1,200–1,500 words plus exhibits, roughly four to six pages. Export
to PDF and upload to Brightspace. Prose over bullet points where a sentence will
do; the writing is graded alongside the code.

---

## 1. What I did

The question, the corpus, and the measure, in one short paragraph. A reader who
has not seen the assignment should understand what was tested.

## 2. Data construction

Universe, sample window, forms, and every filter, with **Table 1** (the waterfall).
State the parsing decisions you made and what they cost: table-stripping threshold,
tokenisation, how many filings failed to parse, how many lost a share count.

State how you handled point-in-time: the day-0 rule, how many filings it moved,
and where your share counts came from.

## 3. Word lists

Sizes of each list. How you rebuilt H4N-Inf and how it differs from the paper's
4,187 forms. The spot check on TAX, COSTS, CAPITAL, LIABILITY.

## 4. Method

The two weighting schemes, with equation (1) written out and your reading of the
ambiguous terms. The regression specification and the standard errors, with a
sentence on why you clustered the way you did.

## 5. Results

**Table 2** summary statistics · **Table 3** top thirty words per list ·
**Figure 1** median excess return by quintile · **Table 4** regressions.

Answer the five questions from the brief here, in order. Question 5 (power) must
appear before you interpret Table 4.

## 6. 10-K versus 10-Q

What differs, and whether the tone-return relation differs with it.

## 7. Limitations

Survivorship in this universe, with a number. Sample size and what it can detect.
Benchmark choice. Anything you tried that did not work — list every specification
you ran, not only the one you are reporting.

## 8. What I would do next

Two or three sentences. What is the single change that would most improve this
test, and what would it cost?
