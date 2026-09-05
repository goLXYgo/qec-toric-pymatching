from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import stim

from ..decoder import decode_memory_experiment
from ..noise import NoiseModel


class PeterShorCodeGenerator:
    """Generate a nine-qubit Peter Shor memory experiment using MPP checks."""

    data_qubits = tuple(range(9))
    z_checks = ((0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8))
    x_checks = ((0, 1, 2, 3, 4, 5), (3, 4, 5, 6, 7, 8))

    def __init__(self, rounds: int, noise: NoiseModel | None = None):
        if rounds <= 0:
            raise ValueError("rounds must be greater than zero")
        self.rounds = rounds
        self.noise = noise or NoiseModel()

    @staticmethod
    def _pauli_product(pauli: str, qubits: Iterable[int]) -> list[stim.GateTarget]:
        target = stim.target_x if pauli == "X" else stim.target_z
        result: list[stim.GateTarget] = []
        for k, qubit in enumerate(qubits):
            if k:
                result.append(stim.target_combiner())
            result.append(target(qubit))
        return result

    def _append_clifford_noise(self, circuit: stim.Circuit, targets: list[int]) -> None:
        p = self.noise.after_clifford_depolarization
        if p > 0:
            circuit.append("DEPOLARIZE1" if len(targets) == 1 else "DEPOLARIZE2", targets, p)

    def _append_encoding(self, circuit: stim.Circuit, basis: str) -> None:
        circuit.append("R", self.data_qubits)
        if self.noise.after_reset_flip_probability > 0:
            circuit.append("X_ERROR", self.data_qubits, self.noise.after_reset_flip_probability)

        if basis == "Z":
            circuit.append("H", [0, 3, 6])
            for qubit in (0, 3, 6):
                self._append_clifford_noise(circuit, [qubit])
        else:
            circuit.append("H", [0])
            self._append_clifford_noise(circuit, [0])
            for pair in ([0, 3], [0, 6]):
                circuit.append("CX", pair)
                self._append_clifford_noise(circuit, pair)
            circuit.append("H", [0, 3, 6])
            for qubit in (0, 3, 6):
                self._append_clifford_noise(circuit, [qubit])

        for pair in ([0, 1], [0, 2], [3, 4], [3, 5], [6, 7], [6, 8]):
            circuit.append("CX", pair)
            self._append_clifford_noise(circuit, pair)

    def _append_mpp(self, circuit: stim.Circuit, pauli: str, support: Iterable[int]) -> None:
        p = self.noise.before_measure_flip_probability
        if p > 0:
            circuit.append("MPP", self._pauli_product(pauli, support), p)
        else:
            circuit.append("MPP", self._pauli_product(pauli, support))

    def build_memory_experiment(self, basis: str = "Z") -> stim.Circuit:
        if basis not in ("X", "Z"):
            raise ValueError("basis must be 'X' or 'Z'")

        circuit = stim.Circuit()
        for qubit in self.data_qubits:
            circuit.append("QUBIT_COORDS", [qubit], [qubit % 3, qubit // 3])
        self._append_encoding(circuit, basis)
        circuit.append("TICK")

        checks = [("Z", support) for support in self.z_checks]
        checks += [("X", support) for support in self.x_checks]
        for round_index in range(self.rounds):
            p = self.noise.before_round_data_depolarization
            if p > 0:
                circuit.append("DEPOLARIZE1", self.data_qubits, p)
            for pauli, support in checks:
                self._append_mpp(circuit, pauli, support)
            for check_index in range(len(checks)):
                current = -len(checks) + check_index
                targets = [stim.target_rec(current)]
                if round_index:
                    targets.append(stim.target_rec(current - len(checks)))
                circuit.append("DETECTOR", targets, [check_index, 0, round_index])
            circuit.append("TICK")

        if basis == "Z":
            self._append_mpp(circuit, "X", (0, 1, 2))
        else:
            self._append_mpp(circuit, "Z", (0, 3, 6))
        circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
        return circuit


def build_shor_code_circuit_stim(p: float, error_gate: str = "X") -> stim.Circuit:
    """Backward-compatible entry point for the original notebook function."""
    if error_gate not in {"X", "Z"}:
        raise ValueError("error_gate must be either 'X' or 'Z'")
    if not 0 <= p <= 1:
        raise ValueError("p must be between 0 and 1")

    # Select the encoded eigenstate whose logical observable anti-commutes
    # with the requested physical Pauli error.
    basis = "X" if error_gate == "X" else "Z"
    generator = PeterShorCodeGenerator(rounds=1)
    circuit = stim.Circuit()
    generator._append_encoding(circuit, basis)
    if p > 0:
        circuit.append(f"{error_gate}_ERROR", generator.data_qubits, p)
    checks = [("Z", support) for support in generator.z_checks]
    checks += [("X", support) for support in generator.x_checks]
    for pauli, support in checks:
        generator._append_mpp(circuit, pauli, support)
        circuit.append("DETECTOR", [stim.target_rec(-1)])
    if basis == "X":
        generator._append_mpp(circuit, "Z", (0, 3, 6))
    else:
        generator._append_mpp(circuit, "X", (0, 1, 2))
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
    return circuit


def get_logical_error_probability_for_shor_code(
    p: float,
    n_shots: int = 50_000,
    error_gate: str = "X",
    verbose: bool = False,
) -> float:
    circuit = build_shor_code_circuit_stim(p, error_gate=error_gate)
    if verbose:
        print(circuit)
    return decode_memory_experiment(circuit, n_shots).logical_error_rate


def get_logical_error_probability_stim_shor(
    ps: Iterable[float],
    n_shots: int = 50_000,
    error_gate: str = "X",
) -> np.ndarray:
    return np.asarray([
        get_logical_error_probability_for_shor_code(p, n_shots, error_gate)
        for p in ps
    ])


def plot_logical_error_probability_stim_shor(
    ps: Iterable[float],
    p_Ls: Iterable[float],
    ylim: tuple[float, float] = (1e-7, 1.1),
    output_path: str | None = None,
    title: str | None = None,
) -> None:
    """Plot scan results; matplotlib is only required when this is called."""
    from pathlib import Path

    import matplotlib.pyplot as plt

    physical = np.asarray(list(ps), dtype=float)
    logical = np.asarray(list(p_Ls), dtype=float)
    if physical.size == 0 or physical.shape != logical.shape:
        raise ValueError("ps and p_Ls must be non-empty and have matching shapes")
    if np.any(physical <= 0):
        raise ValueError("physical error probabilities must be positive for a log plot")

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = logical > 0
    ax.plot(physical[mask], logical[mask], marker="o", linewidth=2, markersize=8)
    reference = np.logspace(np.log10(physical.min()), np.log10(physical.max()), 300)
    ax.plot(reference, reference, "--", color="dimgray", linewidth=2, label="Unprotected qubit")
    ax.set(xscale="log", yscale="log", xlim=(physical.min(), physical.max()), ylim=ylim,
           xlabel="Physical error probability", ylabel="Logical error probability", title=title)
    ax.grid(True, which="major", linewidth=0.8, alpha=0.6)
    ax.legend(loc="upper right")
    fig.tight_layout()
    if output_path is None:
        plt.show()
    else:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
