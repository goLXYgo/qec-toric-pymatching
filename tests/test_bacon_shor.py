import pytest

from qec_gen import NoiseModel
from qec_gen.bacon_shor import BaconShorCodeGenerator


def test_bacon_shor_generator_accepts_shared_noise_model():
    noise = NoiseModel(after_reset_flip_probability=0.01)
    generator = BaconShorCodeGenerator(distance=3, rounds=3, noise=noise)

    assert generator.noise is noise
    with pytest.raises(NotImplementedError, match="not implemented"):
        generator.build_memory_experiment()
