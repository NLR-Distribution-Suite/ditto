from gdm.distribution.enums import Phase

phase_mapper = {"A": Phase.A, "B": Phase.B, "C": Phase.C}


def normalize_phase_tokens(phase_value, default=None):
    default_phases = ["A", "B", "C"] if default is None else list(default)

    if phase_value is None:
        return default_phases

    phase_text = str(phase_value).strip()
    if not phase_text or phase_text.upper() == "NAN":
        return default_phases

    if "," in phase_text:
        raw_tokens = phase_text.split(",")
    else:
        raw_tokens = list(phase_text)

    phases = []
    for token in raw_tokens:
        phase = token.strip().upper()
        if phase in phase_mapper and phase not in phases:
            phases.append(phase)

    return phases or default_phases
