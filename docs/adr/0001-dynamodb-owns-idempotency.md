# ADR 0001 — DynamoDB owns request idempotency

**Status:** Accepted

A model invocation is non-deterministic and metered. Idempotency therefore sits outside the model in an atomic data-store claim. The stable request id is a business/workflow key supplied by the caller. A completed request returns stored output; an in-flight duplicate does not trigger another inference.

Alternative rejected: process-local caching. Lambda concurrency and cold starts make local memory an invalid authority boundary.
