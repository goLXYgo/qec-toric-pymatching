from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import stim

from .layout import ToricCodeLayout, VertexCoord, PlaquetteCoord, EdgeCoord
from .noise import NoiseModel

@dataclass



class ToricCodeStimCleanXZGenerator:

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

    def _rec(self, abs_index: int) -> stim.GateTarget:
        return stim.target_rec(abs_index - self.measurement_count)

    def _data_targets(self) -> List[int]:
        return [self.layout.data_qid(e) for e in self.layout.data_order]

    def _x_anc_targets(self) -> List[int]:
        return [self.layout.x_anc_qid(v) for v in self.layout.x_anc_order]

    def _z_anc_targets(self) -> List[int]:
        return [self.layout.z_anc_qid(p) for p in self.layout.z_anc_order]

    def _append_after_1q_clifford_noise(self, targets: Iterable[int]) -> None:
        targets = list(targets)
        p = self.noise.after_clifford_depolarization
        if p > 0 and targets:
            self.circuit.append("DEPOLARIZE1", targets, p)

    def _append_after_2q_clifford_noise(self, targets: Iterable[int]) -> None:
        targets = list(targets)
        p = self.noise.after_clifford_depolarization
        if p > 0 and targets:
            self.circuit.append("DEPOLARIZE2", targets, p)

    def _append_before_round_data_noise(self) -> None:
        p = self.noise.before_round_data_depolarization
        if p > 0:
            self.circuit.append("DEPOLARIZE1", self._data_targets(), p)

    def _append_h(self, targets: Iterable[int]) -> None:
        targets = list(targets)
        if not targets:
            return
        self.circuit.append("H", targets)
        self._append_after_1q_clifford_noise(targets)

    # ------------------------------------------------------------------
    # Data prepare / measure
    # ------------------------------------------------------------------

    def _append_prepare_data(self, basis: str) -> None:
        targets = self._data_targets()
        if basis == "Z":
            self.circuit.append("R", targets)
            if self.noise.after_reset_flip_probability > 0:
                self.circuit.append("X_ERROR", targets, self.noise.after_reset_flip_probability)
        elif basis == "X":
            self.circuit.append("RX", targets)
            if self.noise.after_reset_flip_probability > 0:
                self.circuit.append("Z_ERROR", targets, self.noise.after_reset_flip_probability)
        else:
            raise ValueError("basis must be 'X' or 'Z'")

    def _append_measure_data(self, basis: str) -> List[int]:
        targets = self._data_targets()
        if basis == "Z":
            if self.noise.before_measure_flip_probability > 0:
                self.circuit.append("X_ERROR", targets, self.noise.before_measure_flip_probability)
            start = self.measurement_count
            self.circuit.append("M", targets)
        elif basis == "X":
            if self.noise.before_measure_flip_probability > 0:
                self.circuit.append("Z_ERROR", targets, self.noise.before_measure_flip_probability)
            start = self.measurement_count
            self.circuit.append("MX", targets)
        else:
            raise ValueError("basis must be 'X' or 'Z'")

        self.measurement_count += len(targets)
        return list(range(start, start + len(targets)))

    # ------------------------------------------------------------------
    # X-only clean subround
    # ------------------------------------------------------------------

    def _append_reset_x_ancillas(self) -> None:
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

    def _x_pairs_for_step(self, step: int) -> List[int]:
        pairs: List[int] = []
        for v in self.layout.x_anc_order:
            support = self.layout.x_check_support(v)
            a = self.layout.x_anc_qid(v)
            d = self.layout.data_qid(support[step])
            pairs.extend([a, d])
        return pairs

    def _append_x_subround(self) -> Dict[VertexCoord, int]:
        self._append_reset_x_ancillas()
        self.circuit.append("TICK")

        for step in range(4):
            pairs = self._x_pairs_for_step(step)
            if pairs:
                self.circuit.append("CX", pairs)
                self._append_after_2q_clifford_noise(pairs)
            self.circuit.append("TICK")

        x_indices = self._append_measure_x_ancillas()
        self.circuit.append("TICK")

        return {v: x_indices[i] for i, v in enumerate(self.layout.x_anc_order)}

    # ------------------------------------------------------------------
    # Z-only clean subround
    # ------------------------------------------------------------------

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

    def _z_pairs_for_step(self, step: int) -> List[int]:
        pairs: List[int] = []
        for p in self.layout.z_anc_order:
            support = self.layout.z_check_support(p)
            d = self.layout.data_qid(support[step])
            a = self.layout.z_anc_qid(p)
            pairs.extend([d, a])
        return pairs

    def _append_z_subround(self) -> Dict[PlaquetteCoord, int]:
        self._append_reset_z_ancillas()
        self.circuit.append("TICK")

        for step in range(4):
            pairs = self._z_pairs_for_step(step)
            if pairs:
                self.circuit.append("CX", pairs)
                self._append_after_2q_clifford_noise(pairs)
            self.circuit.append("TICK")

        z_indices = self._append_measure_z_ancillas()
        self.circuit.append("TICK")

        return {p: z_indices[i] for i, p in enumerate(self.layout.z_anc_order)}

    # ------------------------------------------------------------------
    # Basis-aware detector helpers
    # ------------------------------------------------------------------

    def _append_x_detectors(
        self,
        basis: str,
        cur_x: Dict[VertexCoord, int],
        prev_x: Dict[VertexCoord, int] | None,
        round_index: int,
        t_sub: int,
    ) -> None:
        last_round = (round_index == self.rounds - 1)

        if prev_x is None:
            if basis == "X":
                for v, cur_idx in cur_x.items():
                    self.circuit.append(
                        "DETECTOR",
                        [self._rec(cur_idx)],
                        [v[0], v[1], t_sub],
                    )
        else:
            if not (basis == "Z" and last_round):
                for v, cur_idx in cur_x.items():
                    self.circuit.append(
                        "DETECTOR",
                        [self._rec(cur_idx), self._rec(prev_x[v])],
                        [v[0], v[1], t_sub],
                    )

    def _append_z_detectors(
        self,
        basis: str,
        cur_z: Dict[PlaquetteCoord, int],
        prev_z: Dict[PlaquetteCoord, int] | None,
        round_index: int,
        t_sub: int,
    ) -> None:
        last_round = (round_index == self.rounds - 1)

        if prev_z is None:
            if basis == "Z":
                for p, cur_idx in cur_z.items():
                    self.circuit.append(
                        "DETECTOR",
                        [self._rec(cur_idx)],
                        [p[0] + 0.5, p[1] + 0.5, t_sub],
                    )
        else:
            if not (basis == "X" and last_round):
                for p, cur_idx in cur_z.items():
                    self.circuit.append(
                        "DETECTOR",
                        [self._rec(cur_idx), self._rec(prev_z[p])],
                        [p[0] + 0.5, p[1] + 0.5, t_sub],
                    )

    # ------------------------------------------------------------------
    # Final closure + observables
    # ------------------------------------------------------------------

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

    def _append_observable_include_z_all(
        self,
        final_data_meas_by_qid: Dict[int, int],
    ) -> None:
        logical_z_loops = self.layout.logical_z_loops()

        for obs_index, name in enumerate(["Z1", "Z2"]):
            if name not in logical_z_loops:
                raise KeyError(
                    f"layout.logical_z_loops() does not contain {name}. "
                    f"Available keys: {list(logical_z_loops.keys())}"
                )

            loop_qids = logical_z_loops[name]
            targets = [self._rec(final_data_meas_by_qid[q]) for q in loop_qids]
            self.circuit.append("OBSERVABLE_INCLUDE", targets, obs_index)

    def _append_observable_include_x_all(
        self,
        final_data_meas_by_qid: Dict[int, int],
    ) -> None:
        logical_x_loops = self.layout.logical_x_loops()

        for obs_index, name in enumerate(["X1", "X2"]):
            if name not in logical_x_loops:
                raise KeyError(
                    f"layout.logical_x_loops() does not contain {name}. "
                    f"Available keys: {list(logical_x_loops.keys())}"
                )

            loop_qids = logical_x_loops[name]
            targets = [self._rec(final_data_meas_by_qid[q]) for q in loop_qids]
            self.circuit.append("OBSERVABLE_INCLUDE", targets, obs_index)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_memory_experiment(self, basis: str = "Z") -> stim.Circuit:
        if basis not in ("X", "Z"):
            raise ValueError("basis must be 'X' or 'Z'")

        self._reset_state()
        self._append_qubit_coords()

        self._append_prepare_data(basis)
        self.circuit.append("TICK")

        prev_x = None
        prev_z = None

        for t in range(self.rounds):
            self._append_before_round_data_noise()

            cur_x = self._append_x_subround()
            self._append_x_detectors(
                basis=basis,
                cur_x=cur_x,
                prev_x=prev_x,
                round_index=t,
                t_sub=2 * t,
            )
            prev_x = cur_x

            cur_z = self._append_z_subround()
            self._append_z_detectors(
                basis=basis,
                cur_z=cur_z,
                prev_z=prev_z,
                round_index=t,
                t_sub=2 * t + 1,
            )
            prev_z = cur_z

        final_data_indices = self._append_measure_data(basis)

        final_data_meas = {
            e: final_data_indices[i]
            for i, e in enumerate(self.layout.data_order)
        }
        final_data_meas_by_qid = {
            self.layout.data_qid(e): final_data_indices[i]
            for i, e in enumerate(self.layout.data_order)
        }

        if basis == "Z":
            assert prev_z is not None
            self._append_final_z_detectors(
                final_data_meas=final_data_meas,
                last_z_meas=prev_z,
                t=2 * self.rounds,
            )
            self._append_observable_include_z_all(final_data_meas_by_qid)

        else:
            assert prev_x is not None
            self._append_final_x_detectors(
                final_data_meas=final_data_meas,
                last_x_meas=prev_x,
                t=2 * self.rounds,
            )
            self._append_observable_include_x_all(final_data_meas_by_qid)

        return self.circuit