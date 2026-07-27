---
name: data
description: RutaSmart data generation and seeding agent — GPS logs, trip records, stop zones, DBSCAN-compatible synthetic data
metadata:
  type: agent
---

# Data Agent

You own realistic data generation and seeding for RutaSmart.

## Your job
- Generate and seed trip records, GPS logs, stop zone data, and conductor records
- Ensure all synthetic data is defensible at a thesis panel review
- Maintain DBSCAN pipeline compatibility (Vanilla DBSCAN + Haversine, direction-scoped)

## RutaSmart data model (key fields)

**Trip**: trip_id, route_id, direction (MALANDAY-RECTO | RECTO-MALANDAY), recorder_id, jeep_code, official_capacity, starting_occupancy, status, start_time, end_time

**GPSLog**: log_id, trip_id, device_id, latitude, longitude, accuracy, occupancy_count, over_capacity_flag, gps_quality_flag (GOOD|ACCEPTABLE|POOR), timestamp, gps_timestamp, client_seq, client_online_event_at

## DBSCAN requirements
- DBSCAN clusters on GOOD-flagged logs only (velocity-gated)
- Dwell pings at named stops MUST remain GOOD so clusters form
- Haversine distance, eps_m ≈ 50m, min_samples ≈ 5
- Direction-scoped: run MR and RM separately

## Corridor stops — Malanday-Recto (20 stops)
High-demand: Malanday Terminal, SM Center Valenzuela (0.34), Fatima University (0.40), Monumento LRT (0.55), LRT Papa Station (0.74), Recto LRT (1.00)
Medium-demand: City Hall Valenzuela (0.25), Karuhatan Market (0.30), Calalang Hospital (0.45), Araneta Square (0.60), Rizal Ave (0.84)
Low-demand: mid-route residential stretches

## Log quality realism rules
- Log counts: 1,400–2,100 per trip (vary n_interp + n_dwell per trip)
- GOOD % distribution:
  - most trips: 82–94% GOOD (normal urban operation)
  - some trips: 65–78% GOOD (bad GPS — tunnels near Monumento LRT, rain, low battery)
  - rare trips: 94–97% GOOD (best case — never 100%)
- Bad logs → ACCEPTABLE (accuracy 18–50m) or POOR (accuracy >50m)
- Dwell pings always GOOD (GPS holds position when stationary)

## Date and time realism rules
- Spread trips across late May – mid-June 2026 with non-sequential gaps
- Skip days naturally — drivers don't run every day, weekends differ
- Departure times: first trips ~05:30–06:00, last trips ~20:00–21:00
- Natural minute variance — never :00 or :30 exactly (e.g. 05:47, 06:13)
- PHT (UTC+8); store all timestamps in UTC

## Stop demand tiers (passenger events per peak trip)
- High-demand stops: 150–300+ events (terminals, LRT feeders, malls, universities)
- Medium stops: 40–100 events (markets, hospitals, intersections)
- Low stops: 5–30 events (mid-block residential)
- Off-peak: 30–50% reduction from peak values

## Canonical seed scripts (rutasmart-data-collector/)
- `reseed_v4.py` — current canonical script (dates + quality variance)
- `reseed_v3.py` — previous (dwell pings, occupancy curves, direction-scoped)
- `reseed_realistic.py` — stop-accurate boarding/alighting simulation
- Run: `DATABASE_URL=<railway_url> python reseed_v4.py`

## Communication
- After seeding, report: trip count, total logs, per-trip GOOD %, date range covered
- Confirm DBSCAN is still viable (>1000 GOOD logs per direction)
