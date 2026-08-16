---
article_id: HC-ACC-301
product_area: account
last_updated: 2026-07-06
---

# Account Data Sync Errors After Migration

## Overview

Separately from payment method sync, a customer's account profile (name, address,
tax jurisdiction, team roster) also has to be synchronized between the legacy billing
ledger and the new unified platform during the migration. Account admins sometimes see
a "sync error" banner on their account settings page, which is unrelated to payment
processing and instead reflects a mismatch in profile data between the two systems.

These sync errors are generally low urgency. The account remains fully usable and
billable while a sync error is outstanding, but it should be resolved before Phase 3
verification, since unresolved profile sync errors are one of the most common reasons
an account's legacy record cannot be decommissioned on schedule.

Most account-level sync errors resolve themselves within an hour as the background
reconciliation job re-runs. If a sync error banner persists for more than a day,
support should investigate using the codes below.

## Account Sync Error Codes

| Error Code | Cause | Fix |
|---|---|---|
| ERR-6055 | The account's registered address changed after the Phase 1 shadow copy was taken, so the legacy and unified records disagree on the address field. | Ask the customer to re-save their address in account settings; this forces a fresh sync of just that field. |
| ERR-6210 | Two admins on the same account edited the team roster at the same time during cutover, creating a profile sync conflict that the automated reconciliation job cannot resolve on its own. | Support must open the account in the `account-admin` conflict-resolution view, manually choose which roster edit to keep, and mark the conflict resolved; this cannot be automated. |
| ERR-6233 | The account's tax ID format is valid under the legacy system's older validation rules but fails the unified platform's stricter format check. | Ask the customer to re-enter their tax ID; if it fails again, escalate to the tax compliance team rather than overriding validation. |

## Related Guidance

Because both payment sync errors and account sync errors can appear around the same
cutover date, confirm with the customer whether the error banner they are describing
is on the payment methods page or the account settings page before assuming which
subsystem is affected.
