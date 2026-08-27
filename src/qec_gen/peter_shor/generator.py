from __future__ import annotations

import stim

from ..noise import NoiseModel


class PeterShorCodeGenerator:
    """Public boundary for the future Peter Shor implementation."""

    def __init__(self, rounds: int, noise: NoiseModel | None = None):
        if rounds <= 0:
            raise ValueError("rounds must be greater than zero")
        self.rounds = rounds
        self.noise = noise or NoiseModel()

    def build_memory_experiment(self, basis: str = "Z") -> stim.Circuit:
        raise NotImplementedError("Peter Shor circuit generation is not implemented yet")
