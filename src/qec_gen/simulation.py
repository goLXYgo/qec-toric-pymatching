from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import stim

from .decoder import decode_memory_experiment


@dataclass(frozen=True)
class SimulationPoint:
    code: str
    distance: int
    rounds: int
    basis: str
    physical_error_rate: float
    shots: int
    logical_errors: int
    logical_error_rate: float


CircuitFactory = Callable[[int, int, float, str], stim.Circuit]


def run_parameter_scan(
    circuit_factory: CircuitFactory,
    *,
    code: str,
    distances: Iterable[int],
    physical_error_rates: Iterable[float],
    rounds: int,
    shots: int,
    basis: str = "Z",
    seed: int | None = None,
) -> list[SimulationPoint]:
    results: list[SimulationPoint] = []
    for distance in distances:
        for error_rate in physical_error_rates:
            circuit = circuit_factory(distance, rounds, error_rate, basis)
            decoded = decode_memory_experiment(circuit, shots, seed=seed)
            results.append(
                SimulationPoint(
                    code=code,
                    distance=distance,
                    rounds=rounds,
                    basis=basis,
                    physical_error_rate=error_rate,
                    shots=shots,
                    logical_errors=decoded.logical_errors,
                    logical_error_rate=decoded.logical_error_rate,
                )
            )
    return results
