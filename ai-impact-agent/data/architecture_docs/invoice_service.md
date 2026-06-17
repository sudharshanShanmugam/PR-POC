# Invoice Service

Generates and delivers customer invoices after successful payment.

## Responsibilities
- PDF invoice generation
- Invoice numbering and storage (S3)
- Email delivery via Notification Service

## Dependencies
- **Payment Service** — triggered by payment success events
- **Order Service** — reads order line items for invoice content
- **Notification Service** — sends invoice email

## Critical Paths
- Invoice generation is asynchronous; failures do not block checkout
- Invoice IDs are globally unique and must never be reused
