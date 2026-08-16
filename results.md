# Week 3 / Task Set A -- Results

Domain: customer support (billing migration help-centre drop). **This run indexes only the 6 new articles under `articles/` -- no historical article corpus is read, indexed, or referenced anywhere in this pipeline.**

**Chunks are stored in a persistent Chroma vector database** at `chroma_db/` (see `retriever.CHROMA_DB_PATH`), not just held in memory. Two Chroma collections are created, `chunks_naive` and `chunks_structure_aware` -- one per chunking strategy -- each holding every chunk's `chunk_id`, `document` (chunk text), and metadata (`source_file`, `article_id`, `product_area`, `last_updated`, `strategy`, `section`). The vectors stored and searched are still our own scikit-learn TF-IDF vectors (no external embedding API, no network call), so retrieval scores are exactly the same TF-IDF cosine similarity as a plain in-memory index -- Chroma is doing persistence and the `where`-filtered nearest-neighbor search, not changing what's being measured. Both collections are dropped and recreated from scratch at the start of every run of `main.py`, so the database only ever contains chunks from the current 6 articles -- it never accumulates chunks from a previous run or from a historical corpus.

## 1. Question set and answer key (written before running retrieval)

| ID | Question | Correct article_id | Correct section | Requires table row |
|---|---|---|---|---|
| Q1 | What does ERR-4032 mean and what's the fix? | HC-BIL-102 | Error Code Reference | yes (ERR-4032) |
| Q2 | What causes ERR-5107 and how do I resolve it? | HC-PAY-201 | Payment Sync Error Codes | yes (ERR-5107) |
| Q3 | What does error code ERR-6210 indicate and what is the fix? | HC-ACC-301 | Account Sync Error Codes | yes (ERR-6210) |
| Q4 | What causes sync errors after the billing migration? | HC-PAY-201 | Why Syncs Fail During Migration | no |
| Q5 | What should account admins expect regarding billing permission roles after the migration cutover? | HC-ACC-302 | Overview | no |
| Q6 | What is the overall timeline for the billing system migration? | HC-BIL-101 | Timeline | no |
| Q7 | What should users do to prepare before their billing migration cutover? | HC-BIL-101 | What You Need To Do | no |
| Q8 | What causes ERR-8021 and how is it fixed? | HC-ACC-302 | Permission Error Codes | yes (ERR-8021) |

Q4 is deliberately ambiguous: HC-PAY-201 (payments) and HC-ACC-301 (account) both discuss a topically overlapping 'sync error' concept. It is used as the metadata-filter demo query in section 3 below.

## 2. Hit-in-top-5 results

| Strategy | Hit-in-top-5 |
|---|---|
| Naive (fixed-size, structure-blind) | 4/8 |
| Structure-aware | 8/8 |

Per-question breakdown (same 8 questions, same embedding/scoring method -- only the chunker changed between the two runs):

| ID | Question | Naive hit | Structure-aware hit |
|---|---|---|---|
| Q1 | What does ERR-4032 mean and what's the fix? | MISS | HIT |
| Q2 | What causes ERR-5107 and how do I resolve it? | MISS | HIT |
| Q3 | What does error code ERR-6210 indicate and what is the fix? | MISS | HIT |
| Q4 | What causes sync errors after the billing migration? | HIT | HIT |
| Q5 | What should account admins expect regarding billing permission roles after the migration cutover? | HIT | HIT |
| Q6 | What is the overall timeline for the billing system migration? | HIT | HIT |
| Q7 | What should users do to prepare before their billing migration cutover? | HIT | HIT |
| Q8 | What causes ERR-8021 and how is it fixed? | MISS | HIT |

### Full ranked results, naive strategy, all 8 questions

**Q1. What does ERR-4032 mean and what's the fix?** -- MISS

```
  1. score=0.1481  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::2  section=None
     text: 'the account\'s Phase 2 cutover completed. | Wait until the "Billing Platform" field shows "Unified", then regen'
  2. score=0.1330  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::3  section=None
     text: 'lookup. | | ERR-4032 | A line item on the invoice references a currency code that was retired during the migra'
  3. score=0.0975  article_id=HC-ACC-302  chunk_id=HC-ACC-302::naive::5  section=None
     text: 'is the only account-permission fix that cannot be self-served under any circumstance. | | ERR-8033 | A Billing'
  4. score=0.0871  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::6  section=None
     text: 'reports an invoice error not listed above, or if applying the listed fix does not resolve it, open a ticket ta'
  5. score=0.0864  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::5  section=None
     text: 'ask engineering to raise the renderer timeout for that account. | | ERR-4099 | A duplicate invoice number was '
```

**Q2. What causes ERR-5107 and how do I resolve it?** -- MISS

```
  1. score=0.1522  article_id=HC-PAY-201  chunk_id=HC-PAY-201::naive::4  section=None
     text: "The customer's card was updated during their own cutover window, leaving the legacy and unified processor mapp"
  2. score=0.0790  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::1  section=None
     text: 'agents see, what causes each one, and how to fix it. If you see an error code that is not listed here, escalat'
  3. score=0.0644  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::2  section=None
     text: "the most common reasons an account's legacy record cannot be decommissioned on schedule. Most account-level sy"
  4. score=0.0611  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::4  section=None
     text: '| Two admins on the same account edited the team roster at the same time during cutover, creating a profile sy'
  5. score=0.0560  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::0  section=None
     text: '# Troubleshooting Invoice Errors After the Migration ## Overview Since the billing migration cutover, a small '
```

**Q3. What does error code ERR-6210 indicate and what is the fix?** -- MISS

```
  1. score=0.2239  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::1  section=None
     text: 'agents see, what causes each one, and how to fix it. If you see an error code that is not listed here, escalat'
  2. score=0.1794  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::3  section=None
     text: "Cause | Fix | |---|---|---| | ERR-6055 | The account's registered address changed after the Phase 1 shadow cop"
  3. score=0.1628  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::6  section=None
     text: 'reports an invoice error not listed above, or if applying the listed fix does not resolve it, open a ticket ta'
  4. score=0.1285  article_id=HC-PAY-201  chunk_id=HC-PAY-201::naive::3  section=None
     text: "— the customer's card still works for actual charges. However, they must still be resolved before the account "
  5. score=0.1284  article_id=HC-PAY-202  chunk_id=HC-PAY-202::naive::2  section=None
     text: 'even though nothing changed on their own integration code. ## Webhook Error Codes | Error Code | Cause | Fix |'
```

**Q4. What causes sync errors after the billing migration?** -- HIT

```
  1. score=0.2650  article_id=HC-PAY-201  chunk_id=HC-PAY-201::naive::0  section=None
     text: '# Payment Sync Errors During the Billing Migration ## Why Syncs Fail During Migration While your account is on'
  2. score=0.1720  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::0  section=None
     text: '# Troubleshooting Invoice Errors After the Migration ## Overview Since the billing migration cutover, a small '
  3. score=0.1395  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::6  section=None
     text: 'Related Guidance Because both payment sync errors and account sync errors can appear around the same cutover d'
  4. score=0.1352  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::0  section=None
     text: "# Account Data Sync Errors After Migration ## Overview Separately from payment method sync, a customer's accou"
  5. score=0.1258  article_id=HC-BIL-101  chunk_id=HC-BIL-101::naive::0  section=None
     text: "# Billing System Migration: What's Changing ## Overview Starting this quarter, we are migrating every customer"
```

**Q5. What should account admins expect regarding billing permission roles after the migration cutover?** -- HIT

```
  1. score=0.1639  article_id=HC-ACC-302  chunk_id=HC-ACC-302::naive::1  section=None
     text: 'and plans), and Billing Owner (can also change who has billing access). Existing admins are mapped to one of t'
  2. score=0.1497  article_id=HC-ACC-302  chunk_id=HC-ACC-302::naive::0  section=None
     text: '# Account Permission Changes for Billing Access ## Overview The unified billing platform introduces a more gra'
  3. score=0.1341  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::0  section=None
     text: "# Account Data Sync Errors After Migration ## Overview Separately from payment method sync, a customer's accou"
  4. score=0.1033  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::0  section=None
     text: '# Troubleshooting Invoice Errors After the Migration ## Overview Since the billing migration cutover, a small '
  5. score=0.1007  article_id=HC-ACC-302  chunk_id=HC-ACC-302::naive::4  section=None
     text: 'previously had billing edit access under the legacy system was deactivated before cutover, so no one on the ac'
```

**Q6. What is the overall timeline for the billing system migration?** -- HIT

```
  1. score=0.1694  article_id=HC-BIL-101  chunk_id=HC-BIL-101::naive::0  section=None
     text: "# Billing System Migration: What's Changing ## Overview Starting this quarter, we are migrating every customer"
  2. score=0.1585  article_id=HC-PAY-201  chunk_id=HC-PAY-201::naive::0  section=None
     text: '# Payment Sync Errors During the Billing Migration ## Why Syncs Fail During Migration While your account is on'
  3. score=0.1366  article_id=HC-BIL-101  chunk_id=HC-BIL-101::naive::2  section=None
     text: 'in the final week of the old system will still be honored under its original terms. ## Timeline The migration '
  4. score=0.1268  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::0  section=None
     text: '# Troubleshooting Invoice Errors After the Migration ## Overview Since the billing migration cutover, a small '
  5. score=0.1172  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::6  section=None
     text: 'reports an invoice error not listed above, or if applying the listed fix does not resolve it, open a ticket ta'
```

**Q7. What should users do to prepare before their billing migration cutover?** -- HIT

```
  1. score=0.2176  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::0  section=None
     text: '# Troubleshooting Invoice Errors After the Migration ## Overview Since the billing migration cutover, a small '
  2. score=0.1694  article_id=HC-BIL-101  chunk_id=HC-BIL-101::naive::0  section=None
     text: "# Billing System Migration: What's Changing ## Overview Starting this quarter, we are migrating every customer"
  3. score=0.1585  article_id=HC-PAY-201  chunk_id=HC-PAY-201::naive::0  section=None
     text: '# Payment Sync Errors During the Billing Migration ## Why Syncs Fail During Migration While your account is on'
  4. score=0.1172  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::6  section=None
     text: 'reports an invoice error not listed above, or if applying the listed fix does not resolve it, open a ticket ta'
  5. score=0.0736  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::0  section=None
     text: "# Account Data Sync Errors After Migration ## Overview Separately from payment method sync, a customer's accou"
```

**Q8. What causes ERR-8021 and how is it fixed?** -- MISS

```
  1. score=0.1822  article_id=HC-ACC-302  chunk_id=HC-ACC-302::naive::3  section=None
     text: 'Viewer to Editor (or to Owner) from the "Billing Access" tab in account settings. If the account has no one cu'
  2. score=0.0876  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::1  section=None
     text: 'agents see, what causes each one, and how to fix it. If you see an error code that is not listed here, escalat'
  3. score=0.0621  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::0  section=None
     text: '# Troubleshooting Invoice Errors After the Migration ## Overview Since the billing migration cutover, a small '
  4. score=0.0282  article_id=HC-ACC-301  chunk_id=HC-ACC-301::naive::3  section=None
     text: "Cause | Fix | |---|---|---| | ERR-6055 | The account's registered address changed after the Phase 1 shadow cop"
  5. score=0.0251  article_id=HC-BIL-102  chunk_id=HC-BIL-102::naive::2  section=None
     text: 'the account\'s Phase 2 cutover completed. | Wait until the "Billing Platform" field shows "Unified", then regen'
```

### Full ranked results, structure-aware strategy, all 8 questions

**Q1. What does ERR-4032 mean and what's the fix?** -- HIT

```
  1. score=0.1221  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::1  section='Error Code Reference'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-4001 | Invoice generation was triggered before the account's "
  2. score=0.1161  article_id=HC-ACC-302  chunk_id=HC-ACC-302::structure_aware::3  section='Permission Error Codes'
     text: '| Error Code | Cause | Fix | |---|---|---| | ERR-8021 | The admin who previously had billing edit access under'
  3. score=0.0873  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::2  section='Escalation Path'
     text: 'If a customer reports an invoice error not listed above, or if applying the listed fix does not resolve it, op'
  4. score=0.0614  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::3  section='Payment Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-5040 | The customer's card was updated during their own cutov"
  5. score=0.0598  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::3  section='Account Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-6055 | The account's registered address changed after the Pha"
```

**Q2. What causes ERR-5107 and how do I resolve it?** -- HIT

```
  1. score=0.1234  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::3  section='Payment Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-5040 | The customer's card was updated during their own cutov"
  2. score=0.0680  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::3  section='Account Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-6055 | The account's registered address changed after the Pha"
  3. score=0.0613  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
  4. score=0.0612  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::2  section='Overview'
     text: 'Most account-level sync errors resolve themselves within an hour as the background reconciliation job re-runs.'
  5. score=0.0470  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::2  section='Escalation Path'
     text: 'If a customer reports an invoice error not listed above, or if applying the listed fix does not resolve it, op'
```

**Q3. What does error code ERR-6210 indicate and what is the fix?** -- HIT

```
  1. score=0.1640  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::3  section='Account Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-6055 | The account's registered address changed after the Pha"
  2. score=0.1521  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::2  section='Escalation Path'
     text: 'If a customer reports an invoice error not listed above, or if applying the listed fix does not resolve it, op'
  3. score=0.1475  article_id=HC-ACC-302  chunk_id=HC-ACC-302::structure_aware::3  section='Permission Error Codes'
     text: '| Error Code | Cause | Fix | |---|---|---| | ERR-8021 | The admin who previously had billing edit access under'
  4. score=0.1009  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
  5. score=0.0918  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::3  section='Payment Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-5040 | The customer's card was updated during their own cutov"
```

**Q4. What causes sync errors after the billing migration?** -- HIT

```
  1. score=0.2023  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::4  section='Related Guidance'
     text: 'Because both payment sync errors and account sync errors can appear around the same cutover date, confirm with'
  2. score=0.1869  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::1  section='Overview'
     text: 'These sync errors are generally low urgency. The account remains fully usable and billable while a sync error '
  3. score=0.1644  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
  4. score=0.1454  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::2  section='Overview'
     text: 'Most account-level sync errors resolve themselves within an hour as the background reconciliation job re-runs.'
  5. score=0.1126  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::1  section='Why Syncs Fail During Migration'
     text: 'The most common trigger for a sync error is a customer updating their card details in the middle of their own '
```

**Q5. What should account admins expect regarding billing permission roles after the migration cutover?** -- HIT

```
  1. score=0.1644  article_id=HC-ACC-302  chunk_id=HC-ACC-302::structure_aware::0  section='Overview'
     text: 'The unified billing platform introduces a more granular permission model than the legacy ledger had. Previousl'
  2. score=0.1315  article_id=HC-ACC-302  chunk_id=HC-ACC-302::structure_aware::1  section='Overview'
     text: 'Support should expect a wave of tickets from customers who find they can no longer edit billing details after '
  3. score=0.1239  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::0  section='Overview'
     text: "Separately from payment method sync, a customer's account profile (name, address, tax jurisdiction, team roste"
  4. score=0.0919  article_id=HC-ACC-302  chunk_id=HC-ACC-302::structure_aware::3  section='Permission Error Codes'
     text: '| Error Code | Cause | Fix | |---|---|---| | ERR-8021 | The admin who previously had billing edit access under'
  5. score=0.0894  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
```

**Q6. What is the overall timeline for the billing system migration?** -- HIT

```
  1. score=0.1671  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::2  section='Escalation Path'
     text: 'If a customer reports an invoice error not listed above, or if applying the listed fix does not resolve it, op'
  2. score=0.1622  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
  3. score=0.1431  article_id=HC-BIL-101  chunk_id=HC-BIL-101::structure_aware::2  section='Timeline'
     text: 'The migration runs in four phases:'
  4. score=0.1244  article_id=HC-BIL-101  chunk_id=HC-BIL-101::structure_aware::0  section='Overview'
     text: "Starting this quarter, we are migrating every customer's billing profile from the legacy ledger service to the"
  5. score=0.0684  article_id=HC-BIL-101  chunk_id=HC-BIL-101::structure_aware::7  section='Frequently Asked Questions'
     text: '**Will my subscription price change?** No. Pricing is unaffected by this migration; only the underlying system'
```

**Q7. What should users do to prepare before their billing migration cutover?** -- HIT

```
  1. score=0.2047  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
  2. score=0.1267  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::2  section='Escalation Path'
     text: 'If a customer reports an invoice error not listed above, or if applying the listed fix does not resolve it, op'
  3. score=0.1085  article_id=HC-BIL-101  chunk_id=HC-BIL-101::structure_aware::2  section='Timeline'
     text: 'The migration runs in four phases:'
  4. score=0.0943  article_id=HC-BIL-101  chunk_id=HC-BIL-101::structure_aware::0  section='Overview'
     text: "Starting this quarter, we are migrating every customer's billing profile from the legacy ledger service to the"
  5. score=0.0519  article_id=HC-BIL-101  chunk_id=HC-BIL-101::structure_aware::7  section='Frequently Asked Questions'
     text: '**Will my subscription price change?** No. Pricing is unaffected by this migration; only the underlying system'
```

**Q8. What causes ERR-8021 and how is it fixed?** -- HIT

```
  1. score=0.1493  article_id=HC-ACC-302  chunk_id=HC-ACC-302::structure_aware::3  section='Permission Error Codes'
     text: '| Error Code | Cause | Fix | |---|---|---| | ERR-8021 | The admin who previously had billing edit access under'
  2. score=0.0669  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
  3. score=0.0467  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::3  section='Payment Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-5040 | The customer's card was updated during their own cutov"
  4. score=0.0455  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::3  section='Account Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-6055 | The account's registered address changed after the Pha"
  5. score=0.0447  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::1  section='Error Code Reference'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-4001 | Invoice generation was triggered before the account's "
```

## 3. Metadata filter demo (product_area)

Query: `What causes sync errors after the billing migration?`  (strategy: `structure_aware`)

Unfiltered top-1 product_area: **account** -- expected/correct product_area: **payments**

**Unfiltered (product_area_filter=None):**

```
  1. score=0.2023  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::4  section='Related Guidance'
     text: 'Because both payment sync errors and account sync errors can appear around the same cutover date, confirm with'
  2. score=0.1869  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::1  section='Overview'
     text: 'These sync errors are generally low urgency. The account remains fully usable and billable while a sync error '
  3. score=0.1644  article_id=HC-BIL-102  chunk_id=HC-BIL-102::structure_aware::0  section='Overview'
     text: 'Since the billing migration cutover, a small number of customers have seen invoice generation fail or produce '
  4. score=0.1454  article_id=HC-ACC-301  chunk_id=HC-ACC-301::structure_aware::2  section='Overview'
     text: 'Most account-level sync errors resolve themselves within an hour as the background reconciliation job re-runs.'
  5. score=0.1126  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::1  section='Why Syncs Fail During Migration'
     text: 'The most common trigger for a sync error is a customer updating their card details in the middle of their own '
```

**Filtered (product_area_filter='payments'):**

```
  1. score=0.1126  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::1  section='Why Syncs Fail During Migration'
     text: 'The most common trigger for a sync error is a customer updating their card details in the middle of their own '
  2. score=0.1124  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::2  section='Why Syncs Fail During Migration'
     text: "Sync errors are cosmetic in the vast majority of cases — the customer's card still works for actual charges. H"
  3. score=0.0696  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::0  section='Why Syncs Fail During Migration'
     text: 'While your account is on the new unified billing platform, payment method records still have to stay synchroni'
  4. score=0.0493  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::4  section='When to Escalate'
     text: 'If a payment sync error persists for more than 24 hours after attempting the listed fix, or if the customer re'
  5. score=0.0356  article_id=HC-PAY-201  chunk_id=HC-PAY-201::structure_aware::3  section='Payment Sync Error Codes'
     text: "| Error Code | Cause | Fix | |---|---|---| | ERR-5040 | The customer's card was updated during their own cutov"
```

Top-1 changed by filtering: **True**

## 4. Generation transcripts

Confidence threshold enforced in code: `0.1` (hard check in `generator.generate_answer`, not a prompt instruction).

### 3 cited answers (answerable questions)

**Q:** What does ERR-4032 mean and what's the fix?

```
refused: False
answer: | ERR-4032 | A line item on the invoice references a currency code that was retired during the migration (for example, a legacy internal test currency "ZZZ" left over from a sandbox account that was never cleaned up). | Support must manually remap the offending line item to the customer's real billing currency using the internal `billing-admin remap-currency` tool, then regenerate the invoice. This cannot be self-served by the customer. | [source: article_id=HC-BIL-102, chunk_id=HC-BIL-102::structure_aware::1]
citations: [{'article_id': 'HC-BIL-102', 'chunk_id': 'HC-BIL-102::structure_aware::1', 'source_file': 'billing-invoice-errors.md'}]
```

**Q:** What does error code ERR-6210 indicate and what is the fix?

```
refused: False
answer: | ERR-6210 | Two admins on the same account edited the team roster at the same time during cutover, creating a profile sync conflict that the automated reconciliation job cannot resolve on its own. | Support must open the account in the `account-admin` conflict-resolution view, manually choose which roster edit to keep, and mark the conflict resolved; this cannot be automated. | [source: article_id=HC-ACC-301, chunk_id=HC-ACC-301::structure_aware::3]
citations: [{'article_id': 'HC-ACC-301', 'chunk_id': 'HC-ACC-301::structure_aware::3', 'source_file': 'account-migration-sync.md'}]
```

**Q:** What should account admins expect regarding billing permission roles after the migration cutover?

```
refused: False
answer: The unified billing platform introduces a more granular permission model than the legacy ledger had. Previously, any account admin could view and edit billing information. [source: article_id=HC-ACC-302, chunk_id=HC-ACC-302::structure_aware::0]
citations: [{'article_id': 'HC-ACC-302', 'chunk_id': 'HC-ACC-302::structure_aware::0', 'source_file': 'account-billing-permissions.md'}]
```

### 3 refusal transcripts (out-of-corpus questions)

**Q:** What is the refund SLA for billing disputes?

```
refused: True
answer: I don't have grounded information in the indexed help-centre articles to answer this confidently, so I'm refusing rather than guessing.
reason: the question's distinctive terms are not sufficiently grounded in any retrieved chunk above the confidence threshold (best coverage=0.00 < 0.5) -- refusing rather than answering from generic topical overlap alone
```

**Q:** Do you support multi-currency invoicing after the migration?

```
refused: True
answer: I don't have grounded information in the indexed help-centre articles to answer this confidently, so I'm refusing rather than guessing.
reason: the question's distinctive terms are not sufficiently grounded in any retrieved chunk above the confidence threshold (best coverage=0.33 < 0.5) -- refusing rather than answering from generic topical overlap alone
```

**Q:** What is the phone number for urgent billing support?

```
refused: True
answer: I don't have grounded information in the indexed help-centre articles to answer this confidently, so I'm refusing rather than guessing.
reason: the question's distinctive terms are not sufficiently grounded in any retrieved chunk above the confidence threshold (best coverage=0.33 < 0.5) -- refusing rather than answering from generic topical overlap alone
```

## 5. Second chunker and metadata fields (before/after)

Before (existing/current strategy -- `naive_chunk`, fixed-size word windows, blind to markdown structure):

```python
def naive_chunk(text, chunk_size_words=70, overlap_words=15):
    words = text.split()
    ...
    for start in sliding_window:
        chunk_text = " ".join(words[start:start+chunk_size_words])
        chunks.append({"text": chunk_text, "section": None})
    # no awareness of '|' table rows -- a chunk boundary can fall
    # inside a table and split a header/row from the rest of the row
```

After (new strategy -- `structure_aware_chunk`, added this task):

```python
def structure_aware_chunk(text):
    # walks the markdown line by line
    # - a run of contiguous '|...|' lines (header + separator + all
    #   data rows) is captured as ONE indivisible chunk
    # - prose is split into paragraph chunks under the current
    #   '#'/'##' heading
    # - a table row can never be separated from its header row
    ...
```

New/required metadata fields attached to every chunk (both strategies), added in `retriever.build_chunks`:

```python
chunk = {
    "chunk_id": f"{record['article_id']}::{strategy_name}::{i}",
    "text": raw_chunk["text"],
    "section": raw_chunk["section"],       # new: derived section heading
    "source_file": record["source_file"],
    "article_id": record["article_id"],
    "product_area": record["product_area"],
    "last_updated": record["last_updated"],
    "strategy": strategy_name,             # new: which chunker produced this
}
```

## 6. Which chunking strategy we're shipping

We are shipping **structure_aware**. On the same 8 known-answer questions, against the same 6 articles, with the same TF-IDF scoring, structure-aware scored 8/8 hit-in-top-5 versus naive's 4/8. The failures line up exactly with what naive_chunk is expected to do wrong: its fixed 70-word windows repeatedly split a troubleshooting table row in half (the error code label ends up in one chunk, the cause/fix text in the next), so a query for a specific error code sometimes retrieves a chunk that only half-contains the answer, or misses the code string entirely if it lands right on a chunk boundary. structure_aware_chunk keeps every table (header + all rows) as one chunk, so a query naming an error code always retrieves the complete row with its full cause and fix together.

## 7. A retrieval result that was worse than expected

**Q1** (`What does ERR-4032 mean and what's the fix?`) missed under the naive strategy. Diagnosis: `naive_chunk` splits table rows across chunk boundaries whenever the 70-word fixed window runs out mid-row. For `ERR-4032`, the row's error-code label and the start of its cause text land in one chunk while the rest of the cause and the entire fix land in the next chunk -- neither chunk contains everything needed, and depending on where the boundary falls the code string itself can end up isolated from the explanatory text that makes it match the query well. This is exactly the 'looks fine until you check a specific fact' failure mode the task warned about: eyeballing chunk 0 or chunk 1 of this article looks reasonable, but the row a user actually needs is fragmented two chunks later.

## 8. Bonus: precision vs completeness

Question: **What is the overall timeline for the billing system migration?** (known-correct: HC-BIL-101, section 'Timeline')

naive hit-in-top-5: True   structure_aware hit-in-top-5: True

**Naive final answer:**

```
in the final week of the old system will still be honored under its original terms. ## Timeline The migration runs in four phases: 1. [source: article_id=HC-BIL-101, chunk_id=HC-BIL-101::naive::2]
```

**Structure-aware final answer:**

```
I don't have grounded information in the indexed help-centre articles to answer this confidently, so I'm refusing rather than guessing.
```

structure_aware_chunk deliberately strips the markdown heading ('## Timeline') out of the chunk body and carries it only as the `section` metadata field, so the Timeline chunk's own text is just "The migration runs in four phases:" -- it never repeats the words 'timeline' or 'system' that the question uses. Our lexical grounding gate (generator._distinctive_coverage) checks the chunk body text for the question's distinctive words and refuses when too few are found, so it refuses here even though retrieval genuinely surfaced the right chunk. naive_chunk keeps the raw heading inline with the prose ('... ## Timeline The migration runs in four phases: 1. ...'), so its chunk coincidentally echoes the query's keywords and clears the same gate. The tension is precision vs. completeness one layer further downstream than the table-row case: structure-aware's cleaner chunk boundary (no redundant heading text bleeding into the body) is the more correct chunk, but a chunk that repeats its own heading is more robust to exactly the kind of literal keyword-grounding check a safety-conscious generator needs.

---

_Generated by `src/main.py`. Ingest report is reproduced verbatim below._

```
======================================================================
INGEST REPORT
======================================================================
Scope: indexing ONLY the 6 new billing-migration articles in articles/. The historical article corpus is NOT touched by this run.
Articles directory: D:\ALL\Ai-sample-application\articles
Successful records: 6
  - account-billing-permissions.md      article_id=HC-ACC-302   product_area=account    last_updated=2026-07-10
  - account-migration-sync.md           article_id=HC-ACC-301   product_area=account    last_updated=2026-07-06
  - billing-invoice-errors.md           article_id=HC-BIL-102   product_area=billing    last_updated=2026-07-02
  - billing-migration-overview.md       article_id=HC-BIL-101   product_area=billing    last_updated=2026-06-28
  - payments-migration-webhooks.md      article_id=HC-PAY-202   product_area=payments   last_updated=2026-07-08
  - payments-sync-issues.md             article_id=HC-PAY-201   product_area=payments   last_updated=2026-07-05
Failed records: 0
Guard self-test (missing source_file): OK: guard raised as expected -> record has no source_file -- failed ingest
======================================================================
```
