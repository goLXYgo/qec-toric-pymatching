from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pymatching
import stim


@dataclass(frozen=True)
class DecodeResult:
    shots: int
    logical_errors: int
    logical_error_rate: float


def decode_memory_experiment(
    circuit: stim.Circuit,
    shots: int,
    *,
    seed: int | None = None,
) -> DecodeResult:
    if shots <= 0:
        raise ValueError("shots must be greater than zero")

    detector_error_model = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(detector_error_model)
    sampler = circuit.compile_detector_sampler(seed=seed)
    detection_events, observable_flips = sampler.sample(
        shots=shots,
        separate_observables=True,
    )
    predictions = matching.decode_batch(detection_events)
    failed = np.any(predictions != observable_flips, axis=1)
    logical_errors = int(np.count_nonzero(failed))

    return DecodeResult(
        shots=shots,
        logical_errors=logical_errors,
        logical_error_rate=logical_errors / shots,
    )
