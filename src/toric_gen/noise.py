from dataclasses import dataclass


@dataclass
class NoiseModel:
    before_round_data_depolarization: float = 0.0
    after_clifford_depolarization: float = 0.0
    before_measure_flip_probability: float = 0.0
    after_reset_flip_probability: float = 0.0