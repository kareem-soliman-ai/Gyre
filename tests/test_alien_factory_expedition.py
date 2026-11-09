"""Contract tests for the five-minute Alien Factory expedition."""

from __future__ import annotations

import pytest

from gyre.challenge.expedition import AlienFactoryExpedition
from gyre.challenge.observer_effects import DisclosureLevel, ProbeInstrument


def test_standard_mission_exposes_stable_ids_but_no_semantic_names():
    mission = AlienFactoryExpedition(seed=419)
    assert mission.variable_ids == ("xeno-17", "xeno-42", "xeno-88")
    assert all(
        entry.alias is None for entry in mission.status().notebook_entries
    )
    for variable_id in mission.variable_ids:
        prior = mission.prior_for(variable_id)
        assert prior.observer_effect_possible
        assert prior.exact_profile is None


def test_participant_can_name_and_rename_a_variable_without_changing_its_id():
    mission = AlienFactoryExpedition(seed=419)
    first = mission.name_variable("xeno-17", "light-following flock")
    second = mission.name_variable("xeno-17", "scan-reactive field")
    assert first.variable_id == second.variable_id == "xeno-17"
    assert second.alias == "scan-reactive field"


def test_hypotheses_are_revisable_notebook_entries_not_world_truth():
    mission = AlienFactoryExpedition(seed=419)
    entry = mission.add_hypothesis(
        "xeno-17",
        "The phenomenon strengthens after active scans.",
        confidence=0.65,
    )
    assert entry.hypotheses[0].confidence == pytest.approx(0.65)
    assert "strengthens" in entry.hypotheses[0].statement
    with pytest.raises(ValueError):
        mission.add_hypothesis("xeno-17", "Impossible certainty", confidence=1.2)


def test_active_scan_changes_world_but_reference_scan_is_causally_quiet():
    active_mission = AlienFactoryExpedition(seed=419)
    reference_mission = AlienFactoryExpedition(seed=419)
    active = active_mission.observe(
        "xeno-17",
        ProbeInstrument.ACTIVE,
        intensity=1.0,
    )
    reference = reference_mission.observe(
        "xeno-17",
        ProbeInstrument.REFERENCE,
        intensity=1.0,
    )
    assert active.reading == pytest.approx(reference.reading)

    active_outcome = active_mission.finish()
    reference_outcome = reference_mission.finish()
    active_state = active_outcome.revealed_worlds["xeno-17"]
    reference_state = reference_outcome.revealed_worlds["xeno-17"]
    assert active_state.latent_state != pytest.approx(reference_state.latent_state)
    assert reference_state.control_gain == pytest.approx(1.0)
    assert reference_state.active_instrument_bias == pytest.approx(0.0)


def test_measurement_disturbed_gain_changes_later_countermeasure():
    disturbed = AlienFactoryExpedition(seed=419)
    quiet = AlienFactoryExpedition(seed=419)
    disturbed.observe("xeno-17", ProbeInstrument.ACTIVE, intensity=1.0)
    quiet.observe("xeno-17", ProbeInstrument.REFERENCE, intensity=1.0)
    disturbed.intervene("xeno-17", -0.5)
    quiet.intervene("xeno-17", -0.5)
    disturbed_state = disturbed.finish().revealed_worlds["xeno-17"].latent_state
    quiet_state = quiet.finish().revealed_worlds["xeno-17"].latent_state
    assert disturbed_state != pytest.approx(quiet_state)


def test_names_and_hypotheses_do_not_change_objective_score():
    named = AlienFactoryExpedition(seed=733)
    unnamed = AlienFactoryExpedition(seed=733)
    named.name_variable("xeno-42", "possible pressure feeder")
    named.add_hypothesis(
        "xeno-42",
        "A passive station should disagree after a strong scan.",
        confidence=0.55,
    )
    for mission in (named, unnamed):
        mission.observe("xeno-42", ProbeInstrument.ACTIVE, intensity=0.5)
        mission.intervene("xeno-42", 0.4)
    assert named.finish().stability_score == pytest.approx(
        unnamed.finish().stability_score
    )


def test_action_budget_and_hurricane_are_enforced():
    mission = AlienFactoryExpedition(seed=419, max_turns=2)
    mission.observe("xeno-17", ProbeInstrument.REFERENCE, intensity=0.0)
    mission.intervene("xeno-17", -0.2)
    assert mission.status().turns_remaining == 0
    with pytest.raises(RuntimeError, match="hurricane"):
        mission.observe("xeno-42", ProbeInstrument.ACTIVE, intensity=0.5)


def test_tutorial_reveals_exact_profile_and_blind_is_research_only():
    tutorial = AlienFactoryExpedition(
        seed=419,
        disclosure=DisclosureLevel.EXACT,
    )
    blind = AlienFactoryExpedition(
        seed=419,
        disclosure=DisclosureLevel.BLIND,
    )
    assert tutorial.prior_for("xeno-17").exact_profile is not None
    assert blind.prior_for("xeno-17").research_only


def test_finished_mission_rejects_more_actions_and_reports_efficiency_separately():
    mission = AlienFactoryExpedition(seed=419)
    mission.observe("xeno-17", ProbeInstrument.ACTIVE, intensity=0.4)
    outcome = mission.finish()
    assert 0.0 <= outcome.stability_score <= 100.0
    assert outcome.active_probes == 1
    assert outcome.reference_probes == 0
    assert outcome.turns_used == 1
    assert outcome.interference_burden > 0.0
    with pytest.raises(RuntimeError, match="finished"):
        mission.intervene("xeno-17", -0.2)
