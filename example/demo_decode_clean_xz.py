from __future__ import annotations

import csv

import numpy as np
import pymatching

from toric_gen import NoiseModel, ToricCodeStimCleanXZGenerator


def run_case(
    basis: str,
    distance: int,
    rounds: int,
    p: float,
    shots: int,
) -> tuple[float, int, float, int, float, int, int, int, int, int]:
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

    # Two-logical-qubit toric memory should track two observables:
    # basis=Z -> Z1, Z2
    # basis=X -> X1, X2
    assert circuit.num_observables == 2, (
        f"Expected 2 observables for two-logical-qubit toric code, "
        f"but got {circuit.num_observables}. "
        f"Check OBSERVABLE_INCLUDE for Z1/Z2 or X1/X2."
    )

    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)

    sampler = circuit.compile_detector_sampler()
    detection_events, observable_flips = sampler.sample(
        shots=shots,
        separate_observables=True,
    )

    predictions = matching.decode_batch(detection_events)

    if predictions.ndim == 1:
        predictions = predictions.reshape(-1, circuit.num_observables)

    # Per-observable failures.
    obs_fail_mask = predictions != observable_flips

    failures_obs0 = int(np.count_nonzero(obs_fail_mask[:, 0]))
    failures_obs1 = int(np.count_nonzero(obs_fail_mask[:, 1]))

    rate_obs0 = failures_obs0 / shots
    rate_obs1 = failures_obs1 / shots

    # Any logical failure: if either logical observable is decoded incorrectly.
    failures_any = int(np.count_nonzero(np.any(obs_fail_mask, axis=1)))
    rate_any = failures_any / shots

    return (
        rate_any,
        failures_any,
        rate_obs0,
        failures_obs0,
        rate_obs1,
        failures_obs1,
        circuit.num_qubits,
        circuit.num_detectors,
        circuit.num_measurements,
        circuit.num_observables,
    )


def main() -> None:
    shots = 100_000

    # Demo distances. Stop at d=15 as requested.
    distances = [3, 5, 7, 9, 11, 13, 15]

    # More useful for 100k shots.
    # These values focus on the region where your toric low-p curves started crossing.
    ps = [
        1e-3,
        2e-3,
        3e-3,
        4e-3,
        5e-3,
        6e-3,
        7e-3,
        8e-3,
        9e-3,
        1e-2,
        1.2e-2,
    ]

    rows: list[dict[str, float | int | str]] = []

    for basis in ["Z", "X"]:
        print(f"===== basis={basis} =====")

        for p in ps:
            print(f"----- p={p:g} -----")

            for distance in distances:
                rounds = distance

                (
                    rate_any,
                    failures_any,
                    rate_obs0,
                    failures_obs0,
                    rate_obs1,
                    failures_obs1,
                    num_qubits,
                    num_detectors,
                    num_measurements,
                    num_observables,
                ) = run_case(
                    basis=basis,
                    distance=distance,
                    rounds=rounds,
                    p=p,
                    shots=shots,
                )

                if basis == "Z":
                    obs0_name = "Z1"
                    obs1_name = "Z2"
                else:
                    obs0_name = "X1"
                    obs1_name = "X2"

                print(
                    f"d={distance}, rounds={rounds}, "
                    f"any_failures={failures_any}/{shots}, "
                    f"any_logical_error_rate={rate_any:.8f}, "
                    f"{obs0_name}_failures={failures_obs0}/{shots}, "
                    f"{obs0_name}_rate={rate_obs0:.8f}, "
                    f"{obs1_name}_failures={failures_obs1}/{shots}, "
                    f"{obs1_name}_rate={rate_obs1:.8f}, "
                    f"num_qubits={num_qubits}, "
                    f"num_detectors={num_detectors}, "
                    f"num_measurements={num_measurements}, "
                    f"num_observables={num_observables}"
                )

                rows.append(
                    {
                        "basis": basis,
                        "p": p,
                        "distance": distance,
                        "rounds": rounds,
                        "shots": shots,
                        "failures_any": failures_any,
                        "logical_error_rate_any": rate_any,
                        "failures_obs0": failures_obs0,
                        "logical_error_rate_obs0": rate_obs0,
                        "failures_obs1": failures_obs1,
                        "logical_error_rate_obs1": rate_obs1,
                        "num_qubits": num_qubits,
                        "num_detectors": num_detectors,
                        "num_measurements": num_measurements,
                        "num_observables": num_observables,
                    }
                )

            print()

        print()

    output_csv = "clean_xz_scan_two_logicals_demo.csv"

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "basis",
                "p",
                "distance",
                "rounds",
                "shots",
                "failures_any",
                "logical_error_rate_any",
                "failures_obs0",
                "logical_error_rate_obs0",
                "failures_obs1",
                "logical_error_rate_obs1",
                "num_qubits",
                "num_detectors",
                "num_measurements",
                "num_observables",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {output_csv}")


if __name__ == "__main__":
    main()