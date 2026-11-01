# Southern California Logistics Operations

## Standard Operating Procedure (SOP): Cold-Chain & Transit Anomalies

**Version:** 2.4  
**Effective Date:** January 2021  
**Confidentiality:** Internal Operations Only

### 1. Temperature Control & Spoilage Prevention

All refrigerated fleets must maintain strict IoT temperature compliance to prevent cargo spoilage.

- **Fresh Perishables:** `IOT_TEMP_VAL_C` must remain between **0.0°C and 4.0°C**.
- **Critical Breach:** If `IOT_TEMP_VAL_C` exceeds **4.0°C**, an immediate cold-chain breach is declared.
- **Mitigation:** The dispatcher must immediately contact the driver to restart the auxiliary cooling unit.
- **Diversion Rule:** If ETA delay is greater than **1 hour**, divert the vehicle to the nearest emergency cold-storage facility.

### 2. Route Congestion & Diversion Tactics

Port congestion heavily impacts SLA compliance.

- **Port of Long Beach / Los Angeles:** If `PRT_CNG_LVL` exceeds **7.0**, standard routing is suspended.
- **Mitigation:** Do not hold freight at the port.
- **Diversion:** Divert active shipments to the **Inland Empire Overflow Depot (San Bernardino)** for cross-docking.

### 3. Risk Classification Triggers

Any shipment classified as **High Risk** where:

- `RISK_CLS_TXT = "High Risk"`
- `DELAY_PROB_DEC > 0.65`

must be escalated to the **Tier 2 Logistics Manager**.
