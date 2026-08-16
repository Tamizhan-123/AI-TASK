---
article_id: HC-ACC-302
product_area: account
last_updated: 2026-07-10
---

# Account Permission Changes for Billing Access

## Overview

The unified billing platform introduces a more granular permission model than the
legacy ledger had. Previously, any account admin could view and edit billing
information. On the new platform, billing access is split into three distinct roles:
Billing Viewer (read-only), Billing Editor (can update payment methods and plans), and
Billing Owner (can also change who has billing access). Existing admins are mapped to
one of these roles automatically at cutover based on their prior activity, but the
mapping is not always what a customer expects.

Support should expect a wave of tickets from customers who find they can no longer
edit billing details after cutover, because they were mapped to Billing Viewer instead
of Billing Editor. This is not a bug; it reflects the new platform requiring an
explicit editor grant rather than assuming all admins should have edit access.

## Fixing a Role That Migrated Incorrectly

Any existing Billing Owner can promote another admin from Viewer to Editor (or to
Owner) from the "Billing Access" tab in account settings. If the account has no one
currently mapped to Billing Owner, support must intervene, since customers cannot
self-serve a missing owner role.

## Permission Error Codes

| Error Code | Cause | Fix |
|---|---|---|
| ERR-8021 | The admin who previously had billing edit access under the legacy system was deactivated before cutover, so no one on the account was mapped to Billing Owner, leaving the account with no one able to grant billing roles. | Support must use the `account-admin grant-billing-owner` tool to assign a Billing Owner manually after verifying the requester's identity; this is the only account-permission fix that cannot be self-served under any circumstance. |
| ERR-8033 | A Billing Viewer attempted an edit action that their role does not permit. | Explain the new role model to the customer and direct them to their account's Billing Owner to request an Editor grant. |

## Note on Overlap With Sync Errors

Because role mapping happens at the same time as the account profile sync described
elsewhere, a customer who is missing billing edit access during their cutover week
should also be checked for an outstanding account sync error, since an unresolved sync
error can delay when the new role mapping takes effect.
