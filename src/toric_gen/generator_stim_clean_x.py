from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import stim

from .layout import ToricCodeLayout, VertexCoord, EdgeCoord


@dataclass
class NoiseModel:
    before_round_data_depolarization: float = 0.0
    after_clifford_depolarization: float = 0.0
    before_measure_flip_probability: float = 0.0
    after_reset_flip_probability: float = 0.0


class ToricCodeStimCleanXGenerator:
    """
    Minimal Stim-clean toric X-memory prototype.

    Scope:
      - memory_X only
      - track X stabilizers only
      - one logical observable: X1
      - intended as a clean prototype that should be much easier to make
        deterministic under Stim than the full mixed X/Z toric circuit

    Important limitation:
      - this is NOT a full toric memory experiment yet
      - Z stabilizer rounds are intentionally omitted in this prototype
    """

    def __init__(self, distance: int, rounds: int, noise: NoiseModel | None = None):
        self.layout = ToricCodeLayout(distance)
        self.rounds = rounds
        self.noise = noise or NoiseModel()

        self.circuit = stim.Circuit()
        self.measurement_count = 0

    # ------------------------------------------------------------------
    # Basic helpers
    # ------------------------------------------------------------------

    def _reset_state(self) -> None:
        self.circuit = stim.Circuit()
        self.measurement_count = 0

    def _append_qubit_coords(self) -> None:
        for q, (x, y) in self.layout.qubit_coords().items():
            self.circuit.append("QUBIT_COORDS", [q], [x, y])

    def _data_targets(self) -> List[int]:
        return [self.layout.data_qid(e) for e in self.layout.data_order]

    def _x_anc_targets(self) -> List[int]:
        return [self.layout.x_anc_qid(v) for v in self.layout.x_anc_order]

    def _append_after_1q_clifford_noise(self, targets: Iterable[int]) -> None:
        p = self.noise.after_clifford_depolarization
        targets = list(targets)
        if p > 0 and targets:
            self.circuit.append("DEPOLARIZE1", targets, p)

    def _append_after_2q_clifford_noise(self, flat_targets: Iterable[int]) -> None:
        p = self.noise.after_clifford_depolarization
        flat_targets = list(flat_targets)
        if p > 0 and flat_targets:
            self.circuit.append("DEPOLARIZE2", flat_targets, p)

    def _append_h(self, targets: Iterable[int]) -> None:
        targets = list(targets)
        if not targets:
            return
        self.circuit.append("H", targets)
        self._append_after_1q_clifford_noise(targets)

    def _append_before_round_data_noise(self) -> None:
        p = self.noise.before_round_data_depolarization
        if p > 0:
            self.circuit.append("DEPOLARIZE1", self._data_targets(), p)

    # ------------------------------------------------------------------
    # Data preparation / measurement
    # ------------------------------------------------------------------

    def _append_prepare_data_x(self) -> None:
        targets = self._data_targets()
        self.circuit.append("RX", targets)
        if self.noise.after_reset_flip_probability > 0:
            self.circuit.append("Z_ERROR", targets, self.noise.after_reset_flip_probability)

    def _append_measure_data_x(self) -> List[int]:
        targets = self._data_targets()
        if self.noise.before_measure_flip_probability > 0:
            self.circuit.append("Z_ERROR", targets, self.noise.before_measure_flip_probability)
        start = self.measurement_count
        self.circuit.append("MX", targets)
        self.measurement_count += len(targets)
        return list(range(start, start + len(targets)))

    # ------------------------------------------------------------------
    # Ancilla helpers
    # ------------------------------------------------------------------

    def _append_reset_x_ancillas(self) -> None:
        """
        In this X-only prototype, ancillas are used as X-check measurement qubits.
        To keep the circuit Stim-clean, we reset them directly in X basis.
        """
        targets = self._x_anc_targets()
        self.circuit.append("RX", targets)
        if self.noise.after_reset_flip_probability > 0:
            self.circuit.append("Z_ERROR", targets, self.noise.after_reset_flip_probability)

    def _append_measure_x_ancillas(self) -> List[int]:
        targets = self._x_anc_targets()
        if self.noise.before_measure_flip_probability > 0:
            self.circuit.append("Z_ERROR", targets, self.noise.before_measure_flip_probability)
        start = self.measurement_count
        self.circuit.append("MRX", targets)
        self.measurement_count += len(targets)
        return list(range(start, start + len(targets)))

    # ------------------------------------------------------------------
    # X-check interaction schedule
    # ------------------------------------------------------------------

    def _x_pairs_for_step(self, step: int) -> List[int]:
        """
        For X stabilizers we use CX(x_anc, data).

        We rely on the ordering returned by layout.x_check_support(...).
        """
        pairs: List[int] = []
        for v in self.layout.x_anc_order:
            support = self.layout.x_check_support(v)
            a = self.layout.x_anc_qid(v)
            d = self.layout.data_qid(support[step])
            pairs.extend([a, d])
        return pairs

    def _append_x_round(self) -> Dict[VertexCoord, int]:
        self._append_before_round_data_noise()

        self._append_reset_x_ancillas()
        self.circuit.append("TICK")

        for step in range(4):
            x_pairs = self._x_pairs_for_step(step)
            if x_pairs:
                self.circuit.append("CX", x_pairs)
                self._append_after_2q_clifford_noise(x_pairs)
            self.circuit.append("TICK")

        x_indices = self._append_measure_x_ancillas()
        self.circuit.append("TICK")

        return {v: x_indices[i] for i, v in enumerate(self.layout.x_anc_order)}

    # ------------------------------------------------------------------
    # Detector / observable helpers
    # ------------------------------------------------------------------

    def _rec(self, abs_index: int) -> stim.GateTarget:
        return stim.target_rec(abs_index - self.measurement_count)

    def _append_first_round_x_detectors(
        self,
        current_x: Dict[VertexCoord, int],
        t: int,
    ) -> None:
        for v, cur_idx in current_x.items():
            self.circuit.append(
                "DETECTOR",
                [self._rec(cur_idx)],
                [v[0], v[1], t],
            )

    def _append_middle_round_x_detectors(
        self,
        current_x: Dict[VertexCoord, int],
        prev_x: Dict[VertexCoord, int],
        t: int,
    ) -> None:
        for v, cur_idx in current_x.items():
            prev_idx = prev_x[v]
            self.circuit.append(
                "DETECTOR",
                [self._rec(cur_idx), self._rec(prev_idx)],
                [v[0], v[1], t],
            )

    def _append_final_x_detectors(
        self,
        final_data_meas: Dict[EdgeCoord, int],
        last_x_meas: Dict[VertexCoord, int],
        t: int,
    ) -> None:
        for v in self.layout.x_anc_order:
            support = self.layout.x_check_support(v)
            targets = [self._rec(last_x_meas[v])]
            targets += [self._rec(final_data_meas[e]) for e in support]
            self.circuit.append(
                "DETECTOR",
                targets,
                [v[0], v[1], t],
            )

    def _append_observable_include_x1(
        self,
        final_data_meas_by_qid: Dict[int, int],
    ) -> None:
        loop_qids = self.layout.logical_x_loops()["X1"]
        targets = [self._rec(final_data_meas_by_qid[q]) for q in loop_qids]
        self.circuit.append("OBSERVABLE_INCLUDE", targets, 0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_memory_experiment_x(self) -> stim.Circuit:
        self._reset_state()
        self._append_qubit_coords()

        # Prepare data in X basis.
        self._append_prepare_data_x()
        self.circuit.append("TICK")

        prev_x = None

        # Repeated X-check rounds only.
        for t in range(self.rounds):
            cur_x = self._append_x_round()

            if prev_x is None:
                self._append_first_round_x_detectors(cur_x, t)
            else:
                self._append_middle_round_x_detectors(cur_x, prev_x, t)

            prev_x = cur_x

        # Final data readout.
        final_data_indices = self._append_measure_data_x()

        final_data_meas = {
            e: final_data_indices[i]
            for i, e in enumerate(self.layout.data_order)
        }
        final_data_meas_by_qid = {
            self.layout.data_qid(e): final_data_indices[i]
            for i, e in enumerate(self.layout.data_order)
        }

        # Final closure and logical observable.
        assert prev_x is not None
        self._append_final_x_detectors(
            final_data_meas=final_data_meas,
            last_x_meas=prev_x,
            t=self.rounds,
        )
        self._append_observable_include_x1(final_data_meas_by_qid)

        return self.circuit