# Southern California Logistics Operations

## Policy: Cargo Condition Handling

**Version:** 1.0  
**Status:** Synthetic project policy for the Cold-Chain Logistics AI Assistant

### 1. Purpose

This policy defines the dispatcher response to abnormal cargo-condition telemetry.

### 2. Cargo Condition Review

`CGO_COND_CD` should be reviewed whenever temperature, route risk, or delay conditions become abnormal.

### 3. Normal Condition

When cargo condition is normal:

- continue standard monitoring;
- verify temperature remains inside the required operating range;
- record any relevant delay or route-risk changes.

### 4. Abnormal Condition

If `CGO_COND_CD` indicates degraded, damaged, compromised, or otherwise abnormal cargo:

1. Verify the latest `IOT_TEMP_VAL_C`.
2. Review recent delay and route-risk indicators.
3. Contact the driver or responsible operator for a physical condition check.
4. Avoid declaring the cargo safe based only on telemetry.
5. Escalate if the cargo condition is abnormal and the shipment is also classified as High Risk.

### 5. Temperature-Related Cargo Risk

If abnormal cargo condition is combined with `IOT_TEMP_VAL_C > 4.0°C` for fresh perishables:

- treat the event as a cold-chain incident;
- follow the mitigation process in the Cold-Chain Incident SOP;
- prioritize transfer to emergency cold storage when delay risk is significant.

### 6. Uncertain Condition

If telemetry is incomplete, stale, or inconsistent:

- do not assume the cargo is compliant;
- report the missing or unreliable data;
- request manual verification before making a final operational decision.
