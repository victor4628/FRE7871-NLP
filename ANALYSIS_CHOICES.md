# Analysis choices beyond the assignment text

The September 7 instructor update now fixes the filters, event windows and
control variables. The analysis follows those requirements directly.

The remaining implementation choices are limited:

| Location | Choice beyond or within an ambiguity in the assignment |
|---|---|
| Text parsing | Preserve visible inline-XBRL content and remove a table when digits exceed 15% of its non-space characters. Keep the starter uppercase tokenizer; do not stem or remove stopwords. |
| Duplicate securities | Treat filings as issuer-level documents and retain GOOGL when the same Alphabet filing appears under GOOG and GOOGL. |
| Dollar volume | Use the mean daily price times volume over trading days [-60,-6], then take its natural logarithm. |
| TF-IDF | Recompute document frequency on the exact corpus used by each pooled or form-specific regression and standardize each language score within that corpus. |
| Inference | Use four Newey-West lags for the 20-quarter aggregate trends and company-clustered standard errors for repeated filing observations. |
| Return precision | Report an approximate 80%-power minimum detectable effect, `(cluster-t critical + 0.842) × clustered SE`. |
| Benchmark check | Re-estimate Table 6 using ARKK rather than SPY. |
| Q1/Q2 case evidence | Compare uncertainty-containing sentences (at least 12 tokens) in successive PayPal annual Risk Factors sections; describe the selected filing's observed return and volatility. |

No shell-company exclusion or other sample filter is added beyond the updated
rules; the required $3 cutoff is applied. No optional size-only or turnover
specification is added. The submitted PDF labels Q1-Q6 and reports all models
produced by the main analysis pipeline.
