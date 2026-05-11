from toric_gen.layout import ToricCodeLayout


def parity_intersection(a, b):
    return len(set(a) & set(b)) % 2


layout = ToricCodeLayout(3)

z_loops = layout.logical_z_loops()
x_loops = layout.logical_x_loops()

for z_name, z_loop in z_loops.items():
    for x_name, x_loop in x_loops.items():
        print(
            f"{z_name} vs {x_name}:",
            parity_intersection(z_loop, x_loop),
        )