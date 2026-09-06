# Assignment 1 report

### Uncertainty and Sentiment Analysis of Quarterly and Annual Financial Reports

FRE-GY 7871 A · NLP and the Investment Process

**Name:**
**NetID:**
**GitHub repo:**

Export to PDF and upload to Brightspace. Keep it short. Prose over bullet points where a sentence will
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

Size of each list and the overlap between them. What that overlap implies for how
independent your two measures really are.

## 4. Method

The two weighting schemes, with equation (1) written out and your reading of the
ambiguous terms. How you aggregated to quarters and what you did about form mix and
firm mix. The regression specifications and the standard errors, with a sentence each
on why you clustered the way you did and why the aggregate trend test needs
Newey-West.

## 5. What the measures are made of

**Table 2** summary statistics, 10-K and 10-Q separately, with the correlation between
the two measures. **Table 3** the thirty most frequent words on each list. Answer Q1
and Q2 here.

## 6. Trends, 2021-2025

**Figure 1** and **Table 4**. State the composition corrections you applied before
describing anything. Give the aggregate trend with both OLS and Newey-West
t-statistics, and lead with the within-firm result. Answer Q3, including which of the
two readings of the trend your own evidence supports.

## 7. Uncertainty, volatility and returns

**Table 5**, reported both with and without the pre-filing volatility control, and the
difference explained. Then **Table 6**, the return test, with the power arithmetic
stated before you interpret it. Answer Q4 and Q6.

## 8. 10-K versus 10-Q

What differs between the two form types, and whether your trend and volatility
results differ with it. Answer Q5.

## 9. Limitations

Survivorship, with a number, including the sharper version of it for the trend work:
survivors are the firms that did not blow up. Twenty quarters is a short series.
Benchmark choice. And every specification you ran, not only the one you are reporting.

## 10. What I would do next

Two or three sentences. What is the single change that would most improve this
test, and what would it cost?
