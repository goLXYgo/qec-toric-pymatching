from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import stim

from .layout import ToricCodeLayout, PlaquetteCoord, EdgeCoord
from .noise import NoiseModel

@dataclass


class ToricCodeStimCleanZGenerator:
    """
    Minimal Stim-clean toric Z-memory prototype.

    Scope:
      - memory_Z only
      - track Z stabilizers only
      - one logical observable: Z1
      - intended as a clean prototype that should be much easier to make
        deterministic under Stim than the full mixed X/Z toric circuit

    Important limitation:
      - this is NOT a full toric memory experiment yet
      - X stabilizer rounds are intentionally omitted in this prototype
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

    def _z_anc_targets(self) -> List[int]:
        return [self.layout.z_anc_qid(p) for p in self.layout.z_anc_order]

    def _append_after_2q_clifford_noise(self, flat_targets: Iterable[int]) -> None:
        p = self.noise.after_clifford_depolarization
        flat_targets = list(flat_targets)
        if p > 0 and flat_targets:
            self.circuit.append("DEPOLARIZE2", flat_targets, p)

    def _append_before_round_data_noise(self) -> None:
        p = self.noise.before_round_data_depolarization
        if p > 0:
            self.circuit.append("DEPOLARIZE1", self._data_targets(), p)

    def _append_prepare_data_z(self) -> None:
        targets = self._data_targets()
        self.circuit.append("R", targets)
        if self.noise.after_reset_flip_probability > 0:
            self.circuit.append("X_ERROR", targets, self.noise.after_reset_flip_probability)

    def _append_measure_data_z(self) -> List[int]:
        targets = self._data_targets()
        if self.noise.before_measure_flip_probability > 0:
            self.circuit.append("X_ERROR", targets, self.noise.before_measure_flip_probability)
        start = self.measurement_count
        self.circuit.append("M", targets)
        self.measurement_count += len(targets)
        return list(range(start, start + len(targets)))

    def _append_reset_z_ancillas(self) -> None:
        targets = self._z_anc_targets()
        self.circuit.append("R", targets)
        if self.noise.after_reset_flip_probability > 0:
            self.circuit.append("X_ERROR", targets, self.noise.after_reset_flip_probability)

    def _append_measure_z_ancillas(self) -> List[int]:
        targets = self._z_anc_targets()
        if self.noise.before_measure_flip_probability > 0:
            self.circuit.append("X_ERROR", targets, self.noise.before_measure_flip_probability)
        start = self.measurement_count
        self.circuit.append("MR", targets)
        self.measurement_count += len(targets)
        return list(range(start, start + len(targets)))

    def _rec(self, abs_index: int) -> stim.GateTarget:
        return stim.target_rec(abs_index - self.measurement_count)

    # ------------------------------------------------------------------
    # Z-check interaction schedule
    # ------------------------------------------------------------------

    def _z_pairs_for_step(self, step: int) -> List[int]:
        """
        For Z stabilizers we use CX(data, z_anc).

        We rely on the ordering returned by layout.z_check_support(...).
        """
        pairs: List[int] = []
        for p in self.layout.z_anc_order:
            support = self.layout.z_check_support(p)
            d = self.layout.data_qid(support[step])
            a = self.layout.z_anc_qid(p)
            pairs.extend([d, a])
        return pairs

    def _append_z_round(self) -> Dict[PlaquetteCoord, int]:
        self._append_before_round_data_noise()

        self._append_reset_z_ancillas()
        self.circuit.append("TICK")

        for step in range(4):
            z_pairs = self._z_pairs_for_step(step)
            if z_pairs:
                self.circuit.append("CX", z_pairs)
                self._append_after_2q_clifford_noise(z_pairs)
            self.circuit.append("TICK")

        z_indices = self._append_measure_z_ancillas()
        self.circuit.append("TICK")

        return {p: z_indices[i] for i, p in enumerate(self.layout.z_anc_order)}

    # ------------------------------------------------------------------
    # Detector / observable helpers
    # ------------------------------------------------------------------

    def _append_first_round_z_detectors(
        self,
        current_z: Dict[PlaquetteCoord, int],
        t: int,
    ) -> None:
        for p, cur_idx in current_z.items():
            self.circuit.append(
                "DETECTOR",
                [self._rec(cur_idx)],
                [p[0] + 0.5, p[1] + 0.5, t],
            )

    def _append_middle_round_z_detectors(
        self,
        current_z: Dict[PlaquetteCoord, int],
        prev_z: Dict[PlaquetteCoord, int],
        t: int,
    ) -> None:
        for p, cur_idx in current_z.items():
            prev_idx = prev_z[p]
            self.circuit.append(
                "DETECTOR",
                [self._rec(cur_idx), self._rec(prev_idx)],
                [p[0] + 0.5, p[1] + 0.5, t],
            )

    def _append_final_z_detectors(
        self,
        final_data_meas: Dict[EdgeCoord, int],
        last_z_meas: Dict[PlaquetteCoord, int],
        t: int,
    ) -> None:
        for p in self.layout.z_anc_order:
            support = self.layout.z_check_support(p)
            targets = [self._rec(last_z_meas[p])]
            targets += [self._rec(final_data_meas[e]) for e in support]
            self.circuit.append(
                "DETECTOR",
                targets,
                [p[0] + 0.5, p[1] + 0.5, t],
            )

    def _append_observable_include_z1(
        self,
        final_data_meas_by_qid: Dict[int, int],
    ) -> None:
        loop_qids = self.layout.logical_z_loops()["Z1"]
        targets = [self._rec(final_data_meas_by_qid[q]) for q in loop_qids]
        self.circuit.append("OBSERVABLE_INCLUDE", targets, 0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_memory_experiment_z(self) -> stim.Circuit:
        self._reset_state()
        self._append_qubit_coords()

        # Prepare data in Z basis.
        self._append_prepare_data_z()
        self.circuit.append("TICK")

        prev_z = None

        # Repeated Z-check rounds only.
        for t in range(self.rounds):
            cur_z = self._append_z_round()

            if prev_z is None:
                self._append_first_round_z_detectors(cur_z, t)
            else:
                self._append_middle_round_z_detectors(cur_z, prev_z, t)

            prev_z = cur_z

        # Final data readout.
        final_data_indices = self._append_measure_data_z()

        final_data_meas = {
            e: final_data_indices[i]
            for i, e in enumerate(self.layout.data_order)
        }
        final_data_meas_by_qid = {
            self.layout.data_qid(e): final_data_indices[i]
            for i, e in enumerate(self.layout.data_order)
        }

        # Final closure and logical observable.
        assert prev_z is not None
        self._append_final_z_detectors(
            final_data_meas=final_data_meas,
            last_z_meas=prev_z,
            t=self.rounds,
        )
        self._append_observable_include_z1(final_data_meas_by_qid)

        return self.circuit