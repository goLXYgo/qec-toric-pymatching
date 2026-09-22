from __future__ import annotations

import stim

from ..noise import NoiseModel


class BaconShorCodeGenerator:
    """Generate a Bacon-Shor memory experiment using stabilizer MPP checks."""
    
    def __init__(self, distance: int, rounds: int, noise: NoiseModel | None = None):
        if distance < 2:
            raise ValueError("distance must be at least two")
        if rounds <= 0:
            raise ValueError("rounds must be greater than zero")
        self.distance = distance
        self.rounds = rounds
        self.noise = noise or NoiseModel()
        self.data_qubits = tuple(range(distance * distance))

    def _append_mpp(self, circuit: stim.Circuit, pauli: str, support: tuple[int, ...]) -> None:
        targets: list[stim.GateTarget] = []
        target = stim.target_x if pauli == "X" else stim.target_z
        for index, qubit in enumerate(support):
            if index:
                targets.append(stim.target_combiner())
            targets.append(target(qubit))
        probability = self.noise.before_measure_flip_probability
        if probability > 0:
            circuit.append("MPP", targets, probability)
        else:
            circuit.append("MPP", targets)

    def _stabilizers(self, pauli: str) -> tuple[tuple[int, ...], ...]:
        d = self.distance
        if pauli == "X":
            return tuple(
                tuple(row * d + column for column in range(d))
                + tuple((row + 1) * d + column for column in range(d))
                for row in range(d - 1)
            )
        return tuple(
            tuple(row * d + column for row in range(d))
            + tuple(row * d + column + 1 for row in range(d))
            for column in range(d - 1)
        )

    def build_memory_experiment(self, basis: str = "Z") -> stim.Circuit:
        if basis not in ("X", "Z"):
            raise ValueError("basis must be 'X' or 'Z'")

        circuit = stim.Circuit()
        d = self.distance
        for qubit in self.data_qubits:
            circuit.append("QUBIT_COORDS", [qubit], [qubit % d, qubit // d])

        if basis == "Z":
            circuit.append("R", self.data_qubits)
            reset_error = self.noise.after_reset_flip_probability
            if reset_error > 0:
                circuit.append("X_ERROR", self.data_qubits, reset_error)
        else:
            circuit.append("RX", self.data_qubits)
            reset_error = self.noise.after_reset_flip_probability
            if reset_error > 0:
                circuit.append("Z_ERROR", self.data_qubits, reset_error)
        circuit.append("TICK")

        checks = [("X", support) for support in self._stabilizers("X")]
        checks += [("Z", support) for support in self._stabilizers("Z")]
        check_count = len(checks)
        deterministic_indices = (
            set(range(self.distance - 1))
            if basis == "X"
            else set(range(self.distance - 1, check_count))
        )
        for round_index in range(self.rounds):
            probability = self.noise.before_round_data_depolarization
            if probability > 0:
                circuit.append("DEPOLARIZE1", self.data_qubits, probability)
            for check_index, (pauli, support) in enumerate(checks):
                self._append_mpp(circuit, pauli, support)
                if round_index or check_index in deterministic_indices:
                    targets = [stim.target_rec(-1)]
                    if round_index:
                        targets.append(stim.target_rec(-check_count - 1))
                    circuit.append("DETECTOR", targets, [check_index, 0, round_index])
            circuit.append("TICK")

        logical_pauli = "Z" if basis == "Z" else "X"
        logical_support = tuple(range(d)) if logical_pauli == "X" else tuple(
            row * d for row in range(d)
        )
        self._append_mpp(circuit, logical_pauli, logical_support)
        circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
        return circuit
