# Threat model

| Threat | Boundary | Control |
|---|---|---|
| Unauthenticated public invocation | API → Lambda | `x-eai-key` checked with constant-time comparison; key stored encrypted in SSM |
| Duplicate/replayed request | Service → model | Atomic DynamoDB claim keyed by stable request id |
| Model returns malformed output | Bedrock → service | Pydantic validation; fail closed |
| Secret leakage in logs | Lambda → CloudWatch | Request message and API key are never logged |
| Over-privileged runtime | Lambda → AWS APIs | Model-specific Bedrock invoke, table-scoped DynamoDB policy, parameter-scoped SSM read |
| AI performs irreversible action | Service boundary | Classifier returns data only; caller owns downstream actions |
| Cloud path unavailable | Caller boundary | Existing production workflow remains the fallback |

Out of scope for this public reference: WAF/rate limiting, private API networking, KMS customer-managed keys, multi-region disaster recovery, and enterprise identity federation.
