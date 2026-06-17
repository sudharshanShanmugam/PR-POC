# Historical PR Summaries

## PR-123: Fix payment timeout
**Files changed:** PaymentService.java, AppConfig.java  
**Result:** Introduced a 5s hard timeout in `validatePayment()`. Caused payment timeout issues in high-load scenarios. Reverted in PR-127.

## PR-201: Order status state machine refactor
**Files changed:** OrderController.java, OrderStatus.java  
**Result:** Simplified order status transitions. No downstream issues. Safe change.

## PR-312: Auth token expiry update
**Files changed:** AuthService.java, SessionConfig.java  
**Result:** Shortened session token TTL from 24h to 2h. Caused increased login frequency complaints. Partially reverted.

## PR-415: Invoice PDF rendering upgrade
**Files changed:** InvoiceGenerator.java, pom.xml  
**Result:** Upgraded PDF library. No impact on payment or order flows. Low risk change.
