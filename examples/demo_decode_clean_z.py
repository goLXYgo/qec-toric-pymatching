from __future__ import annotations

import csv

from qec_gen import NoiseModel, ToricCodeStimCleanXZGenerator, decode_memory_experiment


def run_case(distance: int, rounds: int, p: float, shots: int) -> tuple[float, int]:
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

    circuit = gen.build_memory_experiment(basis="Z")
    result = decode_memory_experiment(circuit, shots)
    return result.logical_error_rate, result.logical_errors


def main() -> None:
    shots = 8000
    rows: list[dict[str, float | int]] = []

    for p in [0.001, 0.003]:
        print(f"===== p={p} =====")
        for distance in [2, 3, 4, 5]:
            rounds = distance
            rate, failures = run_case(
                distance=distance,
                rounds=rounds,
                p=p,
                shots=shots,
            )
            print(
                f"d={distance}, rounds={rounds}, failures={failures}/{shots}, "
                f"logical_error_rate={rate:.6f}"
            )
            rows.append(
                {
                    "p": p,
                    "distance": distance,
                    "rounds": rounds,
                    "shots": shots,
                    "failures": failures,
                    "logical_error_rate": rate,
                }
            )
        print()

    with open("clean_z_scan.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "p",
                "distance",
                "rounds",
                "shots",
                "failures",
                "logical_error_rate",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("wrote clean_z_scan.csv")


if __name__ == "__main__":
    main()
