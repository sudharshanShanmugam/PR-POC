# Payment Service

Handles all payment processing flows including authorization, capture, refund, and retry logic.

## Responsibilities
- Payment authorization against external payment gateway
- Idempotent retry handling for transient failures
- Refund initiation and status tracking

## Dependencies
- **Order Service** — receives order IDs to associate payments
- **Invoice Service** — triggers invoice generation on successful payment
- **Notification Service** — sends payment confirmation emails

## Critical Paths
- `validatePayment()` — synchronous; any exception blocks checkout
- `processPayment()` — calls external gateway; must complete within 5s SLA

## Known Risks
- Retries can cause duplicate charges if idempotency key is not set correctly
- Timeout values are shared with Order Service via `AppConfig.ORDER_TIMEOUT_MS`
