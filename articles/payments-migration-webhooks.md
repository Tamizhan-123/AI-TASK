---
article_id: HC-PAY-202
product_area: payments
last_updated: 2026-07-08
---

# Webhook Failures After the Payments Migration

## What Changed

Customers who subscribe to billing webhooks (for example, to get notified when an
invoice is paid) will notice that webhook events are now dispatched by the unified
platform instead of the legacy ledger once an account reaches Phase 2 cutover. The
event payload shape is unchanged, but the signing key used to sign webhook payloads
is different on the new platform, and events are now dispatched from a new sending
IP range.

If a customer's webhook receiver has the old signing key or the old IP range
hard-coded into an allowlist, their webhook deliveries will start failing right at
cutover, even though nothing changed on their own integration code.

## Webhook Error Codes

| Error Code | Cause | Fix |
|---|---|---|
| ERR-7300 | The customer's webhook receiver is verifying payload signatures against the legacy signing key instead of the new unified-platform signing key issued at cutover. | Direct the customer to their developer dashboard to fetch the new signing key and update their receiver; the old key stops working permanently once Phase 2 completes. |
| ERR-7311 | The customer's firewall or receiver allowlist only permits the legacy sending IP range and is rejecting connections from the new platform's IP range. | Provide the customer the new IP range from the developer dashboard's "Webhook Sending IPs" page and ask them to update their allowlist. |
| ERR-7325 | The webhook event queue for the account backed up because the customer's receiver endpoint was returning timeouts, causing retries to pile up. | Ask the customer to confirm their receiver responds within 10 seconds; support can manually flush the backed-up queue once the receiver is healthy again. |

## Testing Webhooks After Cutover

Customers can send a test event from the developer dashboard at any time to confirm
their receiver is correctly verifying signatures against the new key before relying on
production traffic to surface the problem.
