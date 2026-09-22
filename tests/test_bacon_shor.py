import pytest

from qec_gen import NoiseModel
from qec_gen.bacon_shor import BaconShorCodeGenerator


DISTANCES = (3,)


def print_bacon_shor_circuit(distance: int) -> None:
    circuit = BaconShorCodeGenerator(distance=distance, rounds=3).build_memory_experiment(
        basis="Z"
    )
    print(f"\n=== Bacon-Shor d={distance} text circuit ===")
    print(circuit)


def test_bacon_shor_generator_accepts_shared_noise_model():
    noise = NoiseModel(after_reset_flip_probability=0.01)
    generator = BaconShorCodeGenerator(distance=3, rounds=3, noise=noise)

    assert generator.noise is noise


@pytest.mark.parametrize("distance", DISTANCES)
def test_bacon_shor_circuit_output(distance):
    circuit = BaconShorCodeGenerator(distance=distance, rounds=3).build_memory_experiment("Z")
    print_bacon_shor_circuit(distance)

    assert circuit.num_qubits == distance * distance
    assert circuit.num_detectors > 0
    assert circuit.num_observables == 1


if __name__ == "__main__":
    for distance in DISTANCES:
        print_bacon_shor_circuit(distance)
