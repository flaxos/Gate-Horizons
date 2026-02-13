# Deployment Checklist: Fleet-Group Release Foundation

Use this checklist before enabling fleet-group implementation phases in release candidates.

## 1) Schema compatibility and save loading
- [ ] Load a pre-fleet-group save and confirm no migration errors.
- [ ] Load/save/load round trip still works when `enable_fleet_groups` is `false`.
- [ ] Confirm inactive/unknown fleet-group save fields (if present) do not crash load paths.

## 2) Flag-off behavior safety
- [ ] Verify `enable_fleet_groups` defaults to `false` from a clean settings file.
- [ ] Verify fleet-group UI/action surfaces are suppressed while the flag is off.
- [ ] Verify create/dispatch APIs return controlled `feature_disabled` outcomes when off (no hard failures).

## 3) Telemetry schema validation
- [ ] Confirm event names remain stable and centralized:
  - `fleet_group_created`
  - `fleet_group_order_issued`
  - `fleet_group_order_result`
- [ ] Validate required payload fields are present before emission.
- [ ] Reject/alert on missing required payload keys during local validation.

## 4) Local command checks
Run these commands locally before release cut:

- `python -m pytest gate_horizons/tests/test_settings_manager.py`
- `python -m pytest gate_horizons/tests/test_fleet_group_release_foundation.py`
