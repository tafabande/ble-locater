# Design Decisions

## DD-001

Decision:

Use Random Forest Regressor as the baseline model.

Reason:

Works well on small datasets, requires minimal preprocessing, and provides feature importance.

---

## DD-002

Decision:

Predict distance rather than position.

Reason:

Distance estimation generalizes better and allows classical trilateration to compute position.

---

## DD-003

Decision:

ESP32 transmits feature summaries instead of raw RSSI streams.

Reason:

Reduces bandwidth and simplifies server-side processing.
