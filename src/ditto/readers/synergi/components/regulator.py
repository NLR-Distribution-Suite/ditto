from gdm.distribution.components.distribution_regulator import DistributionRegulator
from gdm.distribution.controllers.distribution_regulator_controller import RegulatorController
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import Phase, ConnectionType, TransformerMounting
from gdm.distribution.equipment.distribution_transformer_equipment import (
    DistributionTransformerEquipment,
    WindingEquipment,
)
from gdm.distribution.common.sequence_pair import SequencePair
from gdm.quantities import ApparentPower
from infrasys.quantities import Voltage, Current, Time
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral, sanitize_name, safe_float
from loguru import logger

_PH_IDX = {"A": "1", "B": "2", "C": "3"}
_REG_PCT_Z = 0.01


class DistributionRegulatorMapper(SynergiMapper):

    synergi_table = "InstRegulators"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections, reg_equipment=None):
        reg_equipment = reg_equipment or {}
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id)
        if section is None:
            return None

        buses = self.map_buses(row, section_id_sections)
        if buses[0] is None or buses[1] is None:
            return None

        phases = self.map_phases(row)
        if not phases:
            return None

        reg_type = str(row.get("RegulatorType", "")).strip()
        dev = reg_equipment.get(reg_type, {})

        reg_kva = self.map_reg_kva(dev)
        num_taps = self.map_num_taps(dev)
        tap_range = self.map_tap_range(dev)
        pt_ratio = self.map_pt_ratio(dev)
        ct_rating = self.map_ct_rating(dev)

        min_tap = 1.0 - tap_range / 100.0
        max_tap = 1.0 + tap_range / 100.0
        tap_step = tap_range / (num_taps / 2) if num_taps > 0 else 0.625

        tap_positions = {
            Phase.A: safe_float(row.get("TapPositionPhase1"), 0),
            Phase.B: safe_float(row.get("TapPositionPhase2"), 0),
            Phase.C: safe_float(row.get("TapPositionPhase3"), 0),
        }

        from_id = str(section.get("FromNodeId", "")).strip()
        feeder, substation = self._lookup_feeder_substation(from_id)

        regulators = []
        for phase in phases:
            ph_letter = phase.value
            ph_idx = _PH_IDX[ph_letter]
            tap_pu = 1.0 + tap_positions[phase] * tap_step / 100.0
            safe_id = sanitize_name(f"{str(row.get('UniqueDeviceId', section_id)).strip()}_{section_id}_{ph_letter}")

            equip = self.map_equipment(safe_id, buses[0], reg_kva, num_taps, min_tap, max_tap, tap_pu)
            controller = self.map_controller(row, ph_letter, ph_idx, buses[1], phase, pt_ratio, ct_rating, num_taps)

            regulators.append(DistributionRegulator(
                name=f"reg_{safe_id}",
                buses=list(buses),
                winding_phases=[[phase], [phase]],
                equipment=equip,
                controllers=[controller],
                substation=substation,
                feeder=feeder,
            ))

        return regulators

    def map_buses(self, row, section_id_sections):
        section_id = str(row["SectionId"]).strip()
        section = section_id_sections.get(section_id, {})
        from_id = sanitize_name(str(section.get("FromNodeId", "")).strip())
        to_id = sanitize_name(str(section.get("ToNodeId", "")).strip())
        from_bus = None
        to_bus = None
        try:
            from_bus = self.system.get_component(DistributionBus, from_id)
        except Exception:
            logger.warning(f"Regulator {section_id}: from bus {from_id} not found")
        try:
            to_bus = self.system.get_component(DistributionBus, to_id)
        except Exception:
            logger.warning(f"Regulator {section_id}: to bus {to_id} not found")
        return [from_bus, to_bus]

    def map_phases(self, row):
        return phases_without_neutral(parse_phases(str(row.get("ConnectedPhases", "ABC"))))

    def map_reg_kva(self, dev):
        return safe_float(dev.get("RegulatorRatedKva"), 500) or 500

    def map_num_taps(self, dev):
        return int(safe_float(dev.get("NumberOfTaps"), 32) or 32)

    def map_tap_range(self, dev):
        return safe_float(dev.get("RaiseAndLowerMaxPercentage"), 10) or 10

    def map_pt_ratio(self, dev):
        return safe_float(dev.get("PTRatio"), 60) or 60

    def map_ct_rating(self, dev):
        return safe_float(dev.get("CTRating"), 100) or 100

    def map_winding(self, name, bus, reg_kva, num_taps, min_tap, max_tap, tap_pu):
        return WindingEquipment(
            name=name,
            resistance=_REG_PCT_Z / 2.0,
            is_grounded=True,
            rated_voltage=bus.rated_voltage,
            voltage_type=bus.voltage_type,
            rated_power=ApparentPower(reg_kva, "kilova"),
            num_phases=1,
            connection_type=ConnectionType.STAR,
            tap_positions=[tap_pu],
            total_taps=num_taps,
            min_tap_pu=min_tap,
            max_tap_pu=max_tap,
        )

    def map_equipment(self, safe_id, from_bus, reg_kva, num_taps, min_tap, max_tap, tap_pu):
        w1 = self.map_winding(f"reg_w1_{safe_id}", from_bus, reg_kva, num_taps, min_tap, max_tap, 1.0)
        w2 = self.map_winding(f"reg_w2_{safe_id}", from_bus, reg_kva, num_taps, min_tap, max_tap, tap_pu)
        return DistributionTransformerEquipment(
            name=f"reg_equip_{safe_id}",
            mounting=TransformerMounting.POLE_MOUNT,
            pct_no_load_loss=0.0,
            pct_full_load_loss=_REG_PCT_Z,
            windings=[w1, w2],
            coupling_sequences=[SequencePair(0, 1)],
            winding_reactances=[_REG_PCT_Z * 0.99],
            is_center_tapped=False,
        )

    def map_controller(self, row, ph_letter, ph_idx, to_bus, phase, pt_ratio, ct_rating, num_taps):
        section_id = str(row["SectionId"]).strip()
        device_id = str(row.get("UniqueDeviceId", section_id)).strip()
        safe_id = sanitize_name(f"{device_id}_{section_id}_{ph_letter}")

        fwd_v = self.map_forward_voltage(row, ph_idx)
        fwd_bw = self.map_bandwidth(row, ph_idx)
        fwd_r = self.map_ldc_r(row, ph_idx)
        fwd_x = self.map_ldc_x(row, ph_idx)
        delay = self.map_delay(row)
        is_reversible = self.map_is_reversible(row)

        return RegulatorController(
            name=f"reg_ctrl_{safe_id}",
            delay=delay,
            v_setpoint=Voltage(fwd_v, "volt"),
            min_v_limit=Voltage(max(fwd_v - fwd_bw / 2, 0.001), "volt"),
            max_v_limit=Voltage(fwd_v + fwd_bw / 2, "volt"),
            pt_ratio=pt_ratio,
            use_ldc=(fwd_r != 0 or fwd_x != 0),
            is_reversible=is_reversible,
            ldc_R=Voltage(fwd_r, "volt"),
            ldc_X=Voltage(fwd_x, "volt"),
            ct_primary=Current(ct_rating, "ampere"),
            max_step=num_taps // 2,
            bandwidth=Voltage(fwd_bw, "volt"),
            controlled_bus=to_bus,
            controlled_phase=phase,
        )

    def map_forward_voltage(self, row, ph_idx):
        return safe_float(row.get(f"ForwardVoltageSettingPhase{ph_idx}"), 124) or 124

    def map_bandwidth(self, row, ph_idx):
        return safe_float(row.get(f"ForwardBWDialPhase{ph_idx}"), 2) or 2

    def map_ldc_r(self, row, ph_idx):
        return safe_float(row.get(f"ForwardRDialPhase{ph_idx}"), 0) or 0

    def map_ldc_x(self, row, ph_idx):
        return safe_float(row.get(f"ForwardXDialPhase{ph_idx}"), 0) or 0

    def map_delay(self, row):
        delay_sec = safe_float(row.get("TimeDelaySec"), 120) or 120
        return Time(delay_sec, "second")

    def map_is_reversible(self, row):
        return str(row.get("ReverseSensingMode", "NR")).strip() != "NR"
