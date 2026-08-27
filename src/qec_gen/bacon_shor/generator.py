from __future__ import annotations

import stim

from ..noise import NoiseModel


class BaconShorCodeGenerator:
    """Public boundary for the future Bacon Shor implementation."""

    def __init__(self, distance: int, rounds: int, noise: NoiseModel | None = None):
        if distance < 2:
            raise ValueError("distance must be at least two")
        if rounds <= 0:
            raise ValueError("rounds must be greater than zero")
        self.distance = distance
        self.rounds = rounds
        self.noise = noise or NoiseModel()

    def build_memory_experiment(self, basis: str = "Z") -> stim.Circuit:
        raise NotImplementedError("Bacon Shor circuit generation is not implemented yet")
