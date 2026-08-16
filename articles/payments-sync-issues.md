---
article_id: HC-PAY-201
product_area: payments
last_updated: 2026-07-05
---

# Payment Sync Errors During the Billing Migration

## Why Syncs Fail During Migration

While your account is on the new unified billing platform, payment method records
still have to stay synchronized with the downstream payment processor (the actual
card networks and bank rails). During the migration window, this sync happens twice:
once against the legacy processor mapping and once against the new one, so the two
records can be reconciled. A sync error means the two processor records disagree with
each other, not that a payment actually failed.

The most common trigger for a sync error is a customer updating their card details in
the middle of their own account's Phase 2 cutover window. Because both the old and new
mapping are being written at nearly the same time, one of them can end up stale. This
is why support sees a spike in payment sync errors that closely tracks each cohort's
cutover schedule.

Sync errors are cosmetic in the vast majority of cases — the customer's card still
works for actual charges. However, they must still be resolved before the account
reaches Phase 3 verification, or reconciliation will flag the account and delay
decommissioning of the legacy record for that customer.

## Payment Sync Error Codes

| Error Code | Cause | Fix |
|---|---|---|
| ERR-5040 | The customer's card was updated during their own cutover window, leaving the legacy and unified processor mappings out of sync. | Trigger a manual re-sync from the account's payment settings page; this reconciles both mappings within a few minutes. |
| ERR-5107 | The payment gateway sync token issued during Phase 1 shadow-copy expired before Phase 2 cutover completed, typically because the account sat in Phase 1 for longer than the usual two weeks. | Support must reissue a fresh sync token using the `payments-admin reissue-token` tool, then re-run the sync job for that account; the customer cannot self-serve this. |
| ERR-5112 | The customer has more than one payment method on file and the sync job could not determine which one is the default. | Ask the customer to explicitly re-select a default payment method, which forces the sync job to re-run with an unambiguous target. |

## When to Escalate

If a payment sync error persists for more than 24 hours after attempting the listed
fix, or if the customer reports an actual failed charge (not just a sync warning),
escalate immediately to the payments on-call rotation rather than continuing to retry
the sync.
