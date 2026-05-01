from __future__ import annotations

import numpy as np
import pymatching
import csv
from toric_gen import NoiseModel, ToricCodeStimCleanXZGenerator


def run_case(
    basis: str,
    distance: int,
    rounds: int,
    p: float,
    shots: int,
) -> tuple[float, int, int, int, int]:
    gen = ToricCodeStimCleanXZGenerator(
        distance=distance,
        rounds=rounds,
        noise=NoiseModel(
            before_round_data_depolarization=p,
            after_clifford_depolarization=p,
            before_measure_flip_probability=p,
            after_reset_flip_probability=p,
        ),
    )

    circuit = gen.build_memory_experiment(basis=basis)
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    sampler = circuit.compile_detector_sampler()

    detection_events, observable_flips = sampler.sample(
        shots=shots,
        separate_observables=True,
    )

    predictions = matching.decode_batch(detection_events)
    if circuit.num_observables == 1:
        predictions = predictions.reshape(-1, 1)

    failures = np.count_nonzero(
        np.any(predictions != observable_flips, axis=1)
    )

    return (
        failures / shots,
        failures,
        circuit.num_qubits,
        circuit.num_detectors,
        circuit.num_measurements,
    )


def main() -> None:
    shots = 10000
    rows: list[dict[str, float | int | str]] = []

    for basis in ["Z", "X"]:
        print(f"===== basis={basis} =====")
        for p in [0.001, 0.003]:
            print(f"----- p={p} -----")
            for distance in [2, 3, 4, 5]:
                rounds = distance

                rate, failures, num_qubits, num_detectors, num_measurements = run_case(
                    basis=basis,
                    distance=distance,
                    rounds=rounds,
                    p=p,
                    shots=shots,
                )

                print(
                    f"d={distance}, rounds={rounds}, "
                    f"failures={failures}/{shots}, "
                    f"logical_error_rate={rate:.6f}, "
                    f"num_qubits={num_qubits}, "
                    f"num_detectors={num_detectors}, "
                    f"num_measurements={num_measurements}"
                )

                rows.append(
                    {
                        "basis": basis,
                        "p": p,
                        "distance": distance,
                        "rounds": rounds,
                        "shots": shots,
                        "failures": failures,
                        "logical_error_rate": rate,
                        "num_qubits": num_qubits,
                        "num_detectors": num_detectors,
                        "num_measurements": num_measurements,
                    }
                )
            print()
        print()

    with open("clean_xz_scan.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "basis",
                "p",
                "distance",
                "rounds",
                "shots",
                "failures",
                "logical_error_rate",
                "num_qubits",
                "num_detectors",
                "num_measurements",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("wrote clean_xz_scan.csv")


if __name__ == "__main__":
    main()