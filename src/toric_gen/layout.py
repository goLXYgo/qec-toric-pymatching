from __future__ import annotations

from typing import Dict, List, Tuple


Coord = Tuple[int, int]
EdgeCoord = Tuple[str, int, int]   # ("h" or "v", x, y)
VertexCoord = Tuple[int, int]
PlaquetteCoord = Tuple[int, int]


class ToricCodeLayout:
    """
    L x L toric code with periodic boundary conditions.

    Conventions:
      horizontal edge ("h", x, y): edge from (x, y) -> (x+1, y)
      vertical edge   ("v", x, y): edge from (x, y) -> (x, y+1)

    Counts:
      data qubits: 2 * L * L
      X ancillas:  L * L
      Z ancillas:  L * L
      total:       4 * L * L
    """

    def __init__(self, distance: int):
        if distance < 2:
            raise ValueError("distance must be >= 2")
        self.L = distance

        self.data_ids: Dict[EdgeCoord, int] = {}
        self.x_anc_ids: Dict[VertexCoord, int] = {}
        self.z_anc_ids: Dict[PlaquetteCoord, int] = {}

        self.data_order: List[EdgeCoord] = []
        self.x_anc_order: List[VertexCoord] = []
        self.z_anc_order: List[PlaquetteCoord] = []

        self._assign_qubit_indices()

    def mod(self, x: int) -> int:
        return x % self.L

    def _assign_qubit_indices(self) -> None:
        q = 0

        # Horizontal data edges
        for y in range(self.L):
            for x in range(self.L):
                e = ("h", x, y)
                self.data_ids[e] = q
                self.data_order.append(e)
                q += 1

        # Vertical data edges
        for y in range(self.L):
            for x in range(self.L):
                e = ("v", x, y)
                self.data_ids[e] = q
                self.data_order.append(e)
                q += 1

        # X ancillas on vertices
        for y in range(self.L):
            for x in range(self.L):
                v = (x, y)
                self.x_anc_ids[v] = q
                self.x_anc_order.append(v)
                q += 1

        # Z ancillas on plaquettes
        for y in range(self.L):
            for x in range(self.L):
                p = (x, y)
                self.z_anc_ids[p] = q
                self.z_anc_order.append(p)
                q += 1

        self.num_qubits = q

    def data_qid(self, e: EdgeCoord) -> int:
        return self.data_ids[(e[0], self.mod(e[1]), self.mod(e[2]))]

    def x_anc_qid(self, v: VertexCoord) -> int:
        x, y = v
        return self.x_anc_ids[(self.mod(x), self.mod(y))]

    def z_anc_qid(self, p: PlaquetteCoord) -> int:
        x, y = p
        return self.z_anc_ids[(self.mod(x), self.mod(y))]

    def x_check_support(self, v: VertexCoord) -> List[EdgeCoord]:
        """
        X stabilizer at vertex (x, y), acting on four incident edges.

        Use parity-dependent order to reduce unwanted ancilla-ancilla coupling.
        """
        x, y = self.mod(v[0]), self.mod(v[1])

        east = ("h", x, y)
        west = ("h", self.mod(x - 1), y)
        north = ("v", x, y)
        south = ("v", x, self.mod(y - 1))

        if (x + y) % 2 == 0:
            # even vertex
            return [east, north, west, south]
        else:
            # odd vertex
            return [east, south, west, north]

    def z_check_support(self, p: PlaquetteCoord) -> List[EdgeCoord]:
        """
        Z stabilizer on plaquette with lower-left corner (x, y).

        Use parity-dependent order to reduce unwanted ancilla-ancilla coupling.
        """
        x, y = self.mod(p[0]), self.mod(p[1])

        left = ("v", x, y)
        bottom = ("h", x, y)
        right = ("v", self.mod(x + 1), y)
        top = ("h", x, self.mod(y + 1))

        if (x + y) % 2 == 0:
            # even plaquette
            return [left, bottom, right, top]
        else:
            # odd plaquette
            return [left, top, right, bottom]

    def logical_z_loops(self) -> Dict[str, List[int]]:
        """
        Two independent primal non-contractible loops.
        """
        loop_x = [self.data_qid(("h", x, 0)) for x in range(self.L)]
        loop_y = [self.data_qid(("v", 0, y)) for y in range(self.L)]
        return {"Z1": loop_x, "Z2": loop_y}

    def logical_x_loops(self) -> Dict[str, List[int]]:
        """
        Two independent dual non-contractible loops.
        """
        loop_x = [self.data_qid(("h", 0, x)) for x in range(self.L)]
        loop_y = [self.data_qid(("v", y, 0)) for y in range(self.L)]
        return {"X1": loop_x, "X2": loop_y}

    def qubit_coords(self) -> Dict[int, Tuple[float, float]]:
        """
        Coordinates for debugging / visualization.
        """
        out: Dict[int, Tuple[float, float]] = {}

        for (kind, x, y), q in self.data_ids.items():
            if kind == "h":
                out[q] = (x + 0.5, y)
            else:
                out[q] = (x, y + 0.5)

        for (x, y), q in self.x_anc_ids.items():
            out[q] = (x, y)

        for (x, y), q in self.z_anc_ids.items():
            out[q] = (x + 0.5, y + 0.5)

        return out