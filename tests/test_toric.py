import pytest

from qec_gen import (
    NoiseModel,
    ToricCodeLayout,
    ToricCodeStimCleanXZGenerator,
    decode_memory_experiment,
    run_parameter_scan,
)


def parity_intersection(a, b):
    return len(set(a) & set(b)) % 2


def test_logical_operators_have_expected_intersections():
    layout = ToricCodeLayout(3)

    intersections = {
        (z_name, x_name): parity_intersection(z_loop, x_loop)
        for z_name, z_loop in layout.logical_z_loops().items()
        for x_name, x_loop in layout.logical_x_loops().items()
    }

    assert intersections == {
        ("Z1", "X1"): 1,
        ("Z1", "X2"): 0,
        ("Z2", "X1"): 0,
        ("Z2", "X2"): 1,
    }


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_noiseless_memory_experiment_decodes_without_errors(basis):
    circuit = ToricCodeStimCleanXZGenerator(
        distance=3,
        rounds=3,
        noise=NoiseModel(),
    ).build_memory_experiment(basis=basis)

    result = decode_memory_experiment(circuit, shots=100, seed=1234)

    assert circuit.num_detectors > 0
    assert circuit.num_observables == 2
    assert result.logical_errors == 0


def test_noise_probabilities_are_validated():
    with pytest.raises(ValueError, match="between 0 and 1"):
        NoiseModel(after_clifford_depolarization=1.1)


def test_parameter_scan_accepts_toric_circuit_factory():
    def factory(distance, rounds, error_rate, basis):
        noise = NoiseModel(before_round_data_depolarization=error_rate)
        return ToricCodeStimCleanXZGenerator(
            distance,
            rounds,
            noise,
        ).build_memory_experiment(basis)

    results = run_parameter_scan(
        factory,
        code="toric",
        distances=[2],
        physical_error_rates=[0.0],
        rounds=2,
        shots=20,
        seed=1234,
    )

    assert len(results) == 1
    assert results[0].code == "toric"
    assert results[0].logical_errors == 0
