import pytest

from qec_gen import NoiseModel, decode_memory_experiment
from qec_gen.peter_shor import PeterShorCodeGenerator, build_shor_code_circuit_stim


def test_peter_shor_generator_accepts_shared_noise_model():
    noise = NoiseModel(before_measure_flip_probability=0.01)
    generator = PeterShorCodeGenerator(rounds=3, noise=noise)

    assert generator.noise is noise
    assert generator.build_memory_experiment().num_detectors == 24


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_noiseless_peter_shor_memory_decodes_without_errors(basis):
    circuit = PeterShorCodeGenerator(rounds=3).build_memory_experiment(basis)
    result = decode_memory_experiment(circuit, shots=100, seed=1234)
    assert circuit.num_observables == 1
    assert result.logical_errors == 0


@pytest.mark.parametrize("error_gate", ["X", "Z"])
def test_original_api_is_decodable(error_gate):
    result = decode_memory_experiment(
        build_shor_code_circuit_stim(0.01, error_gate), shots=100, seed=1234
    )
    assert 0 <= result.logical_error_rate <= 1


def test_peter_shor_rejects_unknown_basis():
    with pytest.raises(ValueError, match="basis"):
        PeterShorCodeGenerator(rounds=1).build_memory_experiment("Y")
