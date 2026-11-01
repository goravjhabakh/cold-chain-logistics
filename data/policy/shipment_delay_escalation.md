# Southern California Logistics Operations

## Policy: Shipment Delay Escalation

**Version:** 1.0  
**Status:** Synthetic project policy for the Cold-Chain Logistics AI Assistant

### 1. Purpose

This policy defines how dispatchers should respond when shipment delay risk increases.

### 2. Delay Monitoring

Dispatchers should review `DELAY_PROB_DEC` together with shipment risk and cargo condition.

- **Low Delay Risk:** `DELAY_PROB_DEC < 0.40`
  - Continue normal monitoring.
  - No escalation is required.

- **Moderate Delay Risk:** `0.40 <= DELAY_PROB_DEC <= 0.65`
  - Increase monitoring frequency.
  - Check route and port congestion conditions.
  - Confirm that cargo condition remains acceptable.

- **High Delay Risk:** `DELAY_PROB_DEC > 0.65`
  - Review `RISK_CLS_TXT`.
  - If the shipment is also classified as **High Risk**, escalate to the **Tier 2 Logistics Manager**.
  - If temperature is outside the approved cold-chain range, follow the Cold-Chain Incident SOP immediately.

### 3. Escalation Priority

The following conditions require priority handling:

1. High delay probability combined with High Risk classification.
2. Delay combined with an active temperature breach.
3. Delay combined with severe port congestion.
4. Delay that may push the shipment beyond a time-sensitive delivery window.

### 4. Dispatcher Notes

A high delay probability alone does not automatically mean cargo is unsafe. The dispatcher should combine delay risk with temperature, cargo condition, congestion, and route risk before deciding the response.
