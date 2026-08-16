---
article_id: HC-BIL-102
product_area: billing
last_updated: 2026-07-02
---

# Troubleshooting Invoice Errors After the Migration

## Overview

Since the billing migration cutover, a small number of customers have seen invoice
generation fail or produce unexpected totals. Most of these are caused by the new
platform enforcing stricter validation than the legacy ledger did. This article lists
the specific error codes customers and support agents see, what causes each one, and
how to fix it. If you see an error code that is not listed here, escalate to the
billing platform team rather than guessing at a fix.

## Error Code Reference

| Error Code | Cause | Fix |
|---|---|---|
| ERR-4001 | Invoice generation was triggered before the account's Phase 2 cutover completed. | Wait until the "Billing Platform" field shows "Unified", then regenerate the invoice. |
| ERR-4015 | The customer's tax jurisdiction on file predates a rate change and no longer matches any configured tax rule. | Ask the customer to re-save their billing address to refresh the tax jurisdiction lookup. |
| ERR-4032 | A line item on the invoice references a currency code that was retired during the migration (for example, a legacy internal test currency "ZZZ" left over from a sandbox account that was never cleaned up). | Support must manually remap the offending line item to the customer's real billing currency using the internal `billing-admin remap-currency` tool, then regenerate the invoice. This cannot be self-served by the customer. |
| ERR-4044 | The invoice PDF renderer timed out because the account has more than 500 line items in a single billing period. | Split the invoice into multiple statements using the "Statement Splitting" admin option, or ask engineering to raise the renderer timeout for that account. |
| ERR-4099 | A duplicate invoice number was generated due to a race condition during high-volume cutover windows. | Void the duplicate and let the platform regenerate a fresh invoice number; do not manually edit invoice numbers. |

## Escalation Path

If a customer reports an invoice error not listed above, or if applying the listed fix
does not resolve it, open a ticket tagged `billing-migration` and include the exact
error code, the account ID, and the invoice ID. Do not attempt to manually edit invoice
totals in the database under any circumstances.
