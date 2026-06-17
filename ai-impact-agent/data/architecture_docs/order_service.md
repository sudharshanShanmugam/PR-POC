# Order Service

Manages the full order lifecycle from creation through fulfillment.

## Responsibilities
- Order creation and validation
- Cart-to-order conversion
- Order status transitions (PENDING → PAID → SHIPPED → DELIVERED)
- Checkout orchestration

## Dependencies
- **Payment Service** — called during checkout to process payment
- **Inventory Service** — checks stock availability before confirming order
- **Notification Service** — sends order confirmation and shipping updates

## Critical Paths
- `OrderController.checkout()` — orchestrates payment + inventory; timeout defined by `ORDER_TIMEOUT_MS`
- Any change to timeout values must be coordinated with Payment Service

## Known Risks
- Increasing `ORDER_TIMEOUT_MS` may cause cascading delays in high-traffic scenarios
- Order validation runs synchronously in the checkout path; performance-sensitive
