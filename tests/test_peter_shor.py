import pytest

from qec_gen import NoiseModel
from qec_gen.peter_shor import PeterShorCodeGenerator


def test_peter_shor_generator_accepts_shared_noise_model():
    noise = NoiseModel(before_measure_flip_probability=0.01)
    generator = PeterShorCodeGenerator(rounds=3, noise=noise)

    assert generator.noise is noise
    with pytest.raises(NotImplementedError, match="not implemented"):
        generator.build_memory_experiment()
