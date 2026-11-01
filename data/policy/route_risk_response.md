# Southern California Logistics Operations

## Policy: Route Risk & Diversion Response

**Version:** 1.0  
**Status:** Synthetic project policy for the Cold-Chain Logistics AI Assistant

### 1. Purpose

This policy defines how dispatchers should respond to increased route and congestion risk.

### 2. Route Risk Review

`RT_RSK_IDX` should be considered together with port congestion and shipment condition.

- **Normal Route Risk**
  - Continue the planned route.
  - Monitor telemetry at the standard interval.

- **Elevated Route Risk**
  - Review current congestion conditions.
  - Check whether the shipment has a high delay probability.
  - Confirm that cargo temperature is stable before continuing.

- **Severe Route Risk**
  - Evaluate alternate routes.
  - Avoid unnecessary dwell time.
  - Escalate when severe route risk is combined with High Risk shipment classification or active cold-chain breach.

### 3. Port Congestion

For Los Angeles / Long Beach operations:

- If `PRT_CNG_LVL > 7.0`, standard port routing should be suspended.
- Active shipments should be redirected according to the Cold-Chain Incident SOP.
- Temperature-sensitive shipments should be prioritized for diversion to reduce dwell time.

### 4. Weather-Aware Routing

When severe weather affects the current shipment location or planned route:

- verify whether weather conditions increase travel time or route risk;
- reassess `DELAY_PROB_DEC`;
- verify cargo temperature stability;
- use alternate routing when operationally appropriate.

### 5. Decision Principle

Route changes should be based on combined operational evidence rather than a single metric.
