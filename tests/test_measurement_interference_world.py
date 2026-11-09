import pytest

from gyre.challenge.observer_effects import (
    DisclosureLevel,
    InterferenceMechanism,
    ObserverEffectProfile,
    ProbeInstrument,
    ReactiveMeasurementWorld,
    counterfactual_probe_pair,
    interference_prior,
)


def _profile(**overrides):
    values = {
        "measurand_shift": 0.2,
        "mechanism_shift": 0.1,
        "instrument_bias_shift": 0.05,
        "mechanism": InterferenceMechanism.LINEAR,
    }
    values.update(overrides)
    return ObserverEffectProfile(**values)


def test_active_measurement_reads_before_it_disturbs_the_measurand():
    world = ReactiveMeasurementWorld(
        initial_state=1.0,
        profile=_profile(),
        observation_noise=0.0,
    )
    observation = world.probe(ProbeInstrument.ACTIVE, intensity=1.0, seed=7)
    assert observation.reading == pytest.approx(1.0)
    assert world.latent_state == pytest.approx(1.2)


def test_measurement_can_change_the_future_control_mechanism():
    world = ReactiveMeasurementWorld(
        initial_state=1.0,
        profile=_profile(measurand_shift=0.0, instrument_bias_shift=0.0),
        observation_noise=0.0,
    )
    world.probe(ProbeInstrument.ACTIVE, intensity=1.0, seed=7)
    assert world.control_gain == pytest.approx(1.1)
    world.act(-1.0)
    assert world.latent_state == pytest.approx(-0.1)


def test_measurement_can_bias_later_measurements_without_moving_state():
    world = ReactiveMeasurementWorld(
        initial_state=1.0,
        profile=_profile(measurand_shift=0.0, mechanism_shift=0.0),
        observation_noise=0.0,
    )
    first = world.probe(ProbeInstrument.ACTIVE, intensity=1.0, seed=7)
    second = world.probe(ProbeInstrument.ACTIVE, intensity=1.0, seed=8)
    assert first.reading == pytest.approx(1.0)
    assert second.reading == pytest.approx(1.05)
    assert world.latent_state == pytest.approx(1.0)


def test_reference_probe_is_a_renewable_negative_control():
    world = ReactiveMeasurementWorld(
        initial_state=1.0,
        profile=_profile(),
        observation_noise=0.0,
    )
    before = world.oracle_state()
    reading = world.probe(ProbeInstrument.REFERENCE, intensity=1.0, seed=7)
    after = world.oracle_state()
    assert reading.reading == pytest.approx(1.0)
    assert after == before


def test_counterfactual_pair_uses_common_noise_and_recovers_each_effect():
    pair = counterfactual_probe_pair(
        initial_state=1.0,
        profile=_profile(),
        observation_noise=0.2,
        intensity=0.75,
        seed=419,
    )
    assert pair.active.reading == pair.reference.reading
    assert pair.measurand_difference == pytest.approx(0.15)
    assert pair.mechanism_difference == pytest.approx(0.075)
    assert pair.instrument_bias_difference == pytest.approx(0.0375)


def test_interference_severity_is_monotone_for_linear_profile():
    weak = _profile(
        measurand_shift=0.1,
        mechanism_shift=0.05,
        instrument_bias_shift=0.01,
    )
    strong = _profile(
        measurand_shift=0.4,
        mechanism_shift=0.2,
        instrument_bias_shift=0.1,
    )
    weak_effect = weak.effect_at(0.8)
    strong_effect = strong.effect_at(0.8)
    assert abs(strong_effect.measurand_shift) > abs(weak_effect.measurand_shift)
    assert abs(strong_effect.mechanism_shift) > abs(weak_effect.mechanism_shift)
    assert abs(strong_effect.instrument_bias_shift) > abs(
        weak_effect.instrument_bias_shift
    )


def test_exact_prior_reveals_profile_but_existence_prior_does_not():
    profile = _profile()
    exact = interference_prior(profile, DisclosureLevel.EXACT)
    existence = interference_prior(profile, DisclosureLevel.EXISTENCE_ONLY)
    assert exact.exact_profile == profile
    assert exact.coefficient_bounds is not None
    assert existence.observer_effect_possible
    assert existence.exact_profile is None
    assert existence.coefficient_bounds is None
    assert set(existence.possible_paths) == {
        "measurement_to_measurand",
        "measurement_to_mechanism",
        "measurement_to_future_measurement",
    }


def test_bounded_prior_reveals_safe_bounds_not_true_coefficients():
    profile = _profile()
    prior = interference_prior(
        profile,
        DisclosureLevel.BOUNDED,
        public_bound=0.5,
    )
    assert prior.exact_profile is None
    assert prior.coefficient_bounds == {
        "measurand_shift": (-0.5, 0.5),
        "mechanism_shift": (-0.5, 0.5),
        "instrument_bias_shift": (-0.5, 0.5),
    }


def test_blind_disclosure_exists_only_for_research_control_cells():
    prior = interference_prior(_profile(), DisclosureLevel.BLIND)
    assert not prior.observer_effect_possible
    assert prior.research_only


@pytest.mark.parametrize(
    "mechanism",
    [
        InterferenceMechanism.LINEAR,
        InterferenceMechanism.SATURATING,
        InterferenceMechanism.THRESHOLD,
    ],
)
def test_all_response_families_are_zero_at_zero_intensity(mechanism):
    effect = _profile(mechanism=mechanism).effect_at(0.0)
    assert effect.measurand_shift == 0.0
    assert effect.mechanism_shift == 0.0
    assert effect.instrument_bias_shift == 0.0


def test_invalid_probe_intensity_is_rejected():
    world = ReactiveMeasurementWorld(
        initial_state=1.0,
        profile=_profile(),
    )
    for intensity in (-0.1, 1.1):
        with pytest.raises(ValueError):
            world.probe(ProbeInstrument.ACTIVE, intensity=intensity, seed=1)

