from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pymatching
import stim


Basis = Literal["X", "Z"]


@dataclass(frozen=True)
class ResultRow:
    code: str
    basis: str
    p: float
    distance: int
    rounds: int
    shots: int
    failures: int
    logical_error_rate: float
    num_qubits: int
    num_detectors: int
    num_observables: int
    num_measurements: int


def make_surface_circuit(
    basis: Basis,
    distance: int,
    rounds: int,
    p: float,
) -> stim.Circuit:
    if basis == "Z":
        task = "surface_code:rotated_memory_z"
    elif basis == "X":
        task = "surface_code:rotated_memory_x"
    else:
        raise ValueError("basis must be 'X' or 'Z'")

    return stim.Circuit.generated(
        task,
        distance=distance,
        rounds=rounds,
        before_round_data_depolarization=p,
        after_clifford_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )


def logical_error_rate_from_circuit(
    circuit: stim.Circuit,
    shots: int,
) -> tuple[float, int]:
    if circuit.num_observables == 0:
        raise ValueError("Circuit has no OBSERVABLE_INCLUDE instructions.")

    dem = circuit.detector_error_model(
        decompose_errors=True,
        allow_gauge_detectors=False,
    )

    matching = pymatching.Matching.from_detector_error_model(dem)
    sampler = circuit.compile_detector_sampler()

    detection_events, observable_flips = sampler.sample(
        shots=shots,
        separate_observables=True,
    )

    predictions = matching.decode_batch(detection_events)

    if predictions.ndim == 1:
        predictions = predictions.reshape(-1, 1)

    if observable_flips.ndim == 1:
        observable_flips = observable_flips.reshape(-1, 1)

    failures = np.count_nonzero(
        np.any(predictions != observable_flips, axis=1)
    )

    return failures / shots, int(failures)


def run_case(
    basis: Basis,
    distance: int,
    rounds: int,
    p: float,
    shots: int,
) -> ResultRow:
    circuit = make_surface_circuit(
        basis=basis,
        distance=distance,
        rounds=rounds,
        p=p,
    )

    rate, failures = logical_error_rate_from_circuit(
        circuit=circuit,
        shots=shots,
    )

    return ResultRow(
        code="surface",
        basis=basis,
        p=p,
        distance=distance,
        rounds=rounds,
        shots=shots,
        failures=failures,
        logical_error_rate=rate,
        num_qubits=circuit.num_qubits,
        num_detectors=circuit.num_detectors,
        num_observables=circuit.num_observables,
        num_measurements=circuit.num_measurements,
    )


def write_csv(path: str, rows: list[ResultRow]) -> None:
    fieldnames = [
        "code",
        "basis",
        "p",
        "distance",
        "rounds",
        "shots",
        "failures",
        "logical_error_rate",
        "num_qubits",
        "num_detectors",
        "num_observables",
        "num_measurements",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(row.__dict__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Stim rotated surface-code memory experiments with PyMatching."
    )

    parser.add_argument(
        "--shots",
        type=int,
        default=300_000,
    )

    parser.add_argument(
        "--distances",
        type=int,
        nargs="+",
        default=[5, 7, 11],
    )

    parser.add_argument(
        "--ps",
        type=float,
        nargs="+",
        default=[
            0.008,
            0.01,
            0.02,
            0.03,
        ],
    )

    parser.add_argument(
        "--bases",
        choices=["X", "Z"],
        nargs="+",
        default=["Z", "X"],
    )

    parser.add_argument(
        "--out",
        type=str,
        default="surface_large_scan.csv",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[ResultRow] = []

    for basis in args.bases:
        print(f"===== surface code, basis={basis} =====")

        for p in args.ps:
            print(f"----- p={p} -----")

            for distance in args.distances:
                rounds = distance

                row = run_case(
                    basis=basis,
                    distance=distance,
                    rounds=rounds,
                    p=p,
                    shots=args.shots,
                )

                rows.append(row)

                print(
                    f"code={row.code}, basis={row.basis}, "
                    f"d={row.distance}, rounds={row.rounds}, p={row.p}, "
                    f"failures={row.failures}/{row.shots}, "
                    f"logical_error_rate={row.logical_error_rate:.8f}, "
                    f"num_qubits={row.num_qubits}, "
                    f"num_detectors={row.num_detectors}, "
                    f"num_observables={row.num_observables}, "
                    f"num_measurements={row.num_measurements}"
                )

            print()

        print()

    write_csv(args.out, rows)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()