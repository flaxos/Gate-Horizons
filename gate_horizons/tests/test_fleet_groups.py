"""Comprehensive unit tests for Fleet Group Management feature."""

import unittest

from gate_horizons.game.ships import FleetGroup, FleetManager, Ship
from gate_horizons.game.telemetry import TelemetryAdapter
from gate_horizons.game.telemetry_events import RoadmapTelemetryEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ship(ship_id: str, location: str = "sol", **kwargs) -> Ship:
    """Create a minimal Ship for testing."""
    return Ship(id=ship_id, name=f"Ship-{ship_id}", location=location, **kwargs)


def _make_fleet_manager(enable: bool = True, ships: list[Ship] | None = None) -> FleetManager:
    fm = FleetManager()
    fm.enable_fleet_groups = enable
    for s in ships or []:
        fm.ships[s.id] = s
    return fm


def _tracking_fleet_manager(enable: bool = True, ships: list[Ship] | None = None):
    """Return (FleetManager, emitted_events_list) with telemetry wired up."""
    emitted = []
    fm = _make_fleet_manager(enable, ships)
    fm._telemetry = TelemetryAdapter(
        lambda event_name, payload: emitted.append((event_name, dict(payload)))
    )
    return fm, emitted


# ---------------------------------------------------------------------------
# TestFleetGroupDataModel
# ---------------------------------------------------------------------------


class TestFleetGroupDataModel:
    def test_auto_generated_id(self):
        g = FleetGroup(name="Alpha")
        assert g.id  # non-empty
        assert len(g.id) == 8

    def test_to_dict_from_dict_roundtrip(self):
        g = FleetGroup(name="Bravo", ship_ids=["a", "b"], system_id="sol", created_turn=5)
        d = g.to_dict()
        g2 = FleetGroup.from_dict(d)
        assert g2.id == g.id
        assert g2.name == g.name
        assert g2.ship_ids == g.ship_ids
        assert g2.system_id == g.system_id
        assert g2.created_turn == g.created_turn

    def test_from_dict_ignores_unknown_keys(self):
        d = {"id": "abc", "name": "X", "ship_ids": [], "system_id": "sol",
             "created_turn": 0, "totally_fake": True}
        g = FleetGroup.from_dict(d)
        assert g.id == "abc"
        assert not hasattr(g, "totally_fake")

    def test_ship_group_id_defaults_none(self):
        s = Ship()
        assert s.group_id is None

    def test_ship_group_id_serialization_roundtrip(self):
        s = Ship(id="s1", group_id="grp1")
        d = s.to_dict()
        assert d["group_id"] == "grp1"
        s2 = Ship.from_dict(d)
        assert s2.group_id == "grp1"


# ---------------------------------------------------------------------------
# TestFleetGroupCreation
# ---------------------------------------------------------------------------


class TestFleetGroupCreation:
    def setup_method(self):
        self.s1 = _make_ship("s1", "sol")
        self.s2 = _make_ship("s2", "sol")
        self.s3 = _make_ship("s3", "proxima")
        self.fm = _make_fleet_manager(True, [self.s1, self.s2, self.s3])

    def test_create_group_succeeds(self):
        grp = self.fm.create_fleet_group("Alpha", ["s1", "s2"], "sol", 1)
        assert grp is not None
        assert grp.name == "Alpha"
        assert grp.ship_ids == ["s1", "s2"]
        assert grp.system_id == "sol"
        assert grp.created_turn == 1
        assert self.s1.group_id == grp.id
        assert self.s2.group_id == grp.id
        assert grp.id in self.fm.fleet_groups

    def test_create_group_returns_none_when_disabled(self):
        self.fm.enable_fleet_groups = False
        grp = self.fm.create_fleet_group("Alpha", ["s1", "s2"], "sol", 1)
        assert grp is None
        assert self.s1.group_id is None

    def test_create_group_fails_different_systems(self):
        grp = self.fm.create_fleet_group("Bad", ["s1", "s3"], "sol", 1)
        assert grp is None

    def test_create_group_fails_ship_already_grouped(self):
        self.fm.create_fleet_group("A", ["s1"], "sol", 1)
        grp = self.fm.create_fleet_group("B", ["s1", "s2"], "sol", 2)
        assert grp is None

    def test_create_group_fails_nonexistent_ship(self):
        grp = self.fm.create_fleet_group("A", ["s1", "ghost"], "sol", 1)
        assert grp is None

    def test_create_group_fails_empty_ship_list(self):
        grp = self.fm.create_fleet_group("A", [], "sol", 1)
        assert grp is None


# ---------------------------------------------------------------------------
# TestFleetGroupDisbandAndModify
# ---------------------------------------------------------------------------


class TestFleetGroupDisbandAndModify:
    def setup_method(self):
        self.s1 = _make_ship("s1", "sol")
        self.s2 = _make_ship("s2", "sol")
        self.s3 = _make_ship("s3", "sol")
        self.fm = _make_fleet_manager(True, [self.s1, self.s2, self.s3])
        self.grp = self.fm.create_fleet_group("Alpha", ["s1", "s2"], "sol", 1)

    def test_disband_clears_group_id(self):
        gid = self.grp.id
        result = self.fm.disband_fleet_group(gid)
        assert result is True
        assert self.s1.group_id is None
        assert self.s2.group_id is None
        assert gid not in self.fm.fleet_groups

    def test_disband_nonexistent_group_returns_false(self):
        assert self.fm.disband_fleet_group("no-such-id") is False

    def test_disband_returns_false_when_disabled(self):
        self.fm.enable_fleet_groups = False
        assert self.fm.disband_fleet_group(self.grp.id) is False

    def test_add_ship_to_group_succeeds(self):
        result = self.fm.add_ship_to_group("s3", self.grp.id)
        assert result is True
        assert self.s3.group_id == self.grp.id
        assert "s3" in self.grp.ship_ids

    def test_add_ship_from_different_system_fails(self):
        s4 = _make_ship("s4", "proxima")
        self.fm.ships["s4"] = s4
        assert self.fm.add_ship_to_group("s4", self.grp.id) is False

    def test_add_ship_already_in_group_fails(self):
        assert self.fm.add_ship_to_group("s1", self.grp.id) is False

    def test_remove_ship_from_group_succeeds(self):
        result = self.fm.remove_ship_from_group("s1")
        assert result is True
        assert self.s1.group_id is None
        assert "s1" not in self.grp.ship_ids
        # Group still exists (s2 remains)
        assert self.grp.id in self.fm.fleet_groups

    def test_remove_last_ship_auto_disbands(self):
        self.fm.remove_ship_from_group("s1")
        self.fm.remove_ship_from_group("s2")
        assert self.grp.id not in self.fm.fleet_groups

    def test_get_group_ships_returns_correct_objects(self):
        ships = self.fm.get_group_ships(self.grp.id)
        ids = {s.id for s in ships}
        assert ids == {"s1", "s2"}


# ---------------------------------------------------------------------------
# TestFleetGroupSerialization
# ---------------------------------------------------------------------------


class TestFleetGroupSerialization:
    def test_fleet_manager_roundtrip_with_groups(self):
        s1 = _make_ship("s1", "sol")
        s2 = _make_ship("s2", "sol")
        fm = _make_fleet_manager(True, [s1, s2])
        grp = fm.create_fleet_group("Alpha", ["s1", "s2"], "sol", 5)

        d = fm.to_dict()
        fm2 = FleetManager.from_dict(d)

        assert fm2.enable_fleet_groups is True
        assert grp.id in fm2.fleet_groups
        g2 = fm2.fleet_groups[grp.id]
        assert g2.name == "Alpha"
        assert g2.ship_ids == ["s1", "s2"]
        assert g2.system_id == "sol"
        assert g2.created_turn == 5
        assert fm2.ships["s1"].group_id == grp.id
        assert fm2.ships["s2"].group_id == grp.id

    def test_from_dict_without_fleet_groups_key_backward_compat(self):
        d = {
            "ships": {},
            "ship_templates": {},
        }
        fm = FleetManager.from_dict(d)
        assert fm.fleet_groups == {}
        assert fm.enable_fleet_groups is False


# ---------------------------------------------------------------------------
# TestFleetGroupTelemetry
# ---------------------------------------------------------------------------


class TestFleetGroupTelemetry:
    def test_create_group_emits_event(self):
        s1 = _make_ship("s1", "sol")
        s2 = _make_ship("s2", "sol")
        fm, emitted = _tracking_fleet_manager(True, [s1, s2])

        grp = fm.create_fleet_group("Alpha", ["s1", "s2"], "sol", 7)
        assert len(emitted) == 1
        event_name, payload = emitted[0]
        assert event_name == "fleet_group_created"
        assert payload["group_id"] == grp.id
        assert payload["ship_count"] == 2
        assert payload["system_id"] == "sol"
        assert payload["turn_index"] == 7

    def test_failed_creation_emits_nothing(self):
        s1 = _make_ship("s1", "sol")
        fm, emitted = _tracking_fleet_manager(True, [s1])

        # Fail: nonexistent ship
        fm.create_fleet_group("Bad", ["s1", "ghost"], "sol", 1)
        assert emitted == []

    def test_disabled_creation_emits_nothing(self):
        s1 = _make_ship("s1", "sol")
        fm, emitted = _tracking_fleet_manager(False, [s1])

        fm.create_fleet_group("X", ["s1"], "sol", 1)
        assert emitted == []


# ---------------------------------------------------------------------------
# TestFleetGroupFeatureSwitch
# ---------------------------------------------------------------------------


class TestFleetGroupFeatureSwitch:
    def setup_method(self):
        self.s1 = _make_ship("s1", "sol")
        self.s2 = _make_ship("s2", "sol")
        self.fm = _make_fleet_manager(True, [self.s1, self.s2])
        self.grp = self.fm.create_fleet_group("Alpha", ["s1", "s2"], "sol", 1)
        # Now disable the feature
        self.fm.enable_fleet_groups = False

    def test_create_blocked(self):
        s3 = _make_ship("s3", "sol")
        self.fm.ships["s3"] = s3
        assert self.fm.create_fleet_group("B", ["s3"], "sol", 2) is None

    def test_disband_blocked(self):
        assert self.fm.disband_fleet_group(self.grp.id) is False

    def test_add_ship_blocked(self):
        s3 = _make_ship("s3", "sol")
        self.fm.ships["s3"] = s3
        assert self.fm.add_ship_to_group("s3", self.grp.id) is False

    def test_remove_ship_blocked(self):
        assert self.fm.remove_ship_from_group("s1") is False

    def test_get_group_ships_still_works(self):
        ships = self.fm.get_group_ships(self.grp.id)
        assert len(ships) == 2
        assert {s.id for s in ships} == {"s1", "s2"}


# ---------------------------------------------------------------------------
# TestSingleShipParity
# ---------------------------------------------------------------------------


class TestSingleShipParity:
    def setup_method(self):
        self.s1 = _make_ship("s1", "sol")
        self.s2 = _make_ship("s2", "sol")
        self.fm = _make_fleet_manager(True, [self.s1, self.s2])
        self.grp = self.fm.create_fleet_group("Alpha", ["s1", "s2"], "sol", 1)

    def test_move_ship_works_on_grouped_ship(self):
        result = self.fm.move_ship("s1", "proxima")
        assert result is True
        assert self.s1.destination == "proxima"
        # Ship remains in group even while moving
        assert self.s1.group_id == self.grp.id

    def test_process_movement_works_on_grouped_ship(self):
        self.fm.move_ship("s1", "proxima")
        mr = self.fm.process_movement("s1")
        assert mr.ship_id == "s1"
        assert mr.current_location == "proxima"
        assert mr.arrived is True

    def test_destroy_ship_removes_from_group(self):
        gid = self.grp.id
        self.fm.destroy_ship("s1")
        assert "s1" not in self.fm.ships
        # s1 removed from group ship list
        assert "s1" not in self.grp.ship_ids
        # s2 still in group
        assert self.s2.group_id == gid

    def test_destroy_last_grouped_ship_disbands_group(self):
        gid = self.grp.id
        self.fm.destroy_ship("s1")
        self.fm.destroy_ship("s2")
        assert gid not in self.fm.fleet_groups
