from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseModel:
    before_round_data_depolarization: float = 0.0
    after_clifford_depolarization: float = 0.0
    before_measure_flip_probability: float = 0.0
    after_reset_flip_probability: float = 0.0

    def __post_init__(self) -> None:
        for name, probability in vars(self).items():
            if not 0.0 <= probability <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
