from gdm.quantities import Distance, Current, ResistancePULength

DEFAULT_BRANCH_LENGTH = Distance(0.001, "km")

DEFAULT_R_MATRIX = [
    [1e-6, 0.0, 0.0],
    [0.0, 1e-6, 0.0],
    [0.0, 0.0, 1e-6],
]


DEFAULT_X_MATRIX = [
    [1e-4, 0.0, 0.0],
    [0.0, 1e-4, 0.0],
    [0.0, 0.0, 1e-4],
]


DEFAULT_C_MATRIX = [
    [0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0],
]

DEFAULT_BRANCH_AMPACITY = Current(600.0, "A")

DEFAULT_BRANCH_RESISTANCE = ResistancePULength(0.555000, "ohm/mile").to("ohm/km")
