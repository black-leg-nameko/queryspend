<!-- queryspend-report:v1 -->
## queryspend cost estimate — SIMULATED DEMO

> Estimate, not an invoice. Unknown values are never treated as $0.

**Decision:** `WARN` — usd_threshold_exceeded  
**Cost:** Known monthly subtotal: **+487.50 USD/month**  
**Coverage:** 2 known / 5 affected; 3 not known  
**Confidence:** `high`  
**USD threshold:** `500.00`

Largest known contributor: `model.northstar_retail.fct_orders` (+675.00 USD/month).

<details>
<summary>Model evidence and uncertainty</summary>

| Model | Change | Monthly delta | Confidence | Status |
|---|---|---:|---|---|
| `model.northstar_retail.dim_customer` | modified | -187.50 USD/month | high | KNOWN |
| `model.northstar_retail.fct_orders` | modified | +675.00 USD/month | high | KNOWN |
| `model.northstar_retail.daily_margin` | unchanged | Unknown — unknown_downstream_data_shape | unknown | UNKNOWN |
| `model.northstar_retail.orders_view` | modified | Unknown — unknown_view_consumer_cost | unknown | UNKNOWN |
| `model.northstar_retail.monthly_kpis` | unchanged | Unknown — unknown_downstream_data_shape | unknown | UNKNOWN |

</details>

Full evidence: `queryspend-report.json`
