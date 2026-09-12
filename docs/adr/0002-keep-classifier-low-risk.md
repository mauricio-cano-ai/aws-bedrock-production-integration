# ADR 0002 — Keep the Bedrock path low-risk

**Status:** Accepted

The service classifies intent/urgency and returns typed data. It cannot send WhatsApp messages or mutate business-critical ownership/state. EasyAIgent can fall back to its existing path on timeout or non-2xx.

This makes rollout reversible and limits blast radius while production evidence is gathered.
