# Operations runbook

## Symptom: elevated 5xx
1. Inspect Lambda error count and duration in CloudWatch.
2. Correlate by AWS request id; do not paste lead text into incident tickets.
3. Check Bedrock throttling/model availability and Lambda timeout.
4. Leave the caller fallback enabled. Do not disable the established path to force traffic through this service.

## Symptom: repeated 409 `request_in_progress`
1. Query the DynamoDB item by `request_id`.
2. Confirm whether an invocation is still active or a previous invocation terminated unexpectedly.
3. Allow TTL/operational cleanup policy to resolve stale claims; do not manually overwrite completed results.

## Symptom: 401 after deployment
1. Verify the SSM parameter name matches `AUTH_PARAM_NAME`.
2. Verify Lambda role can read only that parameter.
3. Rotate the API key if there is any possibility of exposure.
4. Re-run `scripts/smoke_test.ps1`.

## Deployment verification
`sam validate --lint` → `sam build` → deploy → unauthorized 401 → authorized 200 → exact replay `cached=true` → confirm CloudWatch/X-Ray and DynamoDB completed state.
