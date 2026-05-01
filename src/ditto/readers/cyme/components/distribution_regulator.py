from loguru import logger
from infrasys.quantities import Time

from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.common.sequence_pair import SequencePair
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_regulator import DistributionRegulator
from gdm.distribution.controllers.distribution_regulator_controller import RegulatorController
from gdm.distribution.equipment.distribution_transformer_equipment import (
    DistributionTransformerEquipment,
    WindingEquipment,
)
from gdm.distribution.enums import ConnectionType, Phase, VoltageTypes
from gdm.quantities import ApparentPower, Current, Voltage


class DistributionRegulatorMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Network"
    cyme_section = "REGULATOR SETTING"

    def parse(self, row, used_sections, section_id_sections, equipment_data):
        base_name = self.map_name(row)
        section_id = str(row["SectionID"])
        section = section_id_sections.get(section_id)
        if section is None:
            logger.warning(f"Section {section_id} not found for regulator {base_name}. Skipping")
            return None

        equipment_row = equipment_data.get(row["EqID"], None)
        phases = self.map_phases(row, section)
        if not phases:
            logger.warning(f"No phases found for regulator {base_name}. Skipping")
            return None

        buses = self.map_buses(section)
        regulators = []
        for phase in phases:
            phase_suffix = self.map_phase_suffix(phase)
            regulator_name = f"{base_name}_{phase_suffix}" if len(phases) > 1 else base_name
            single_phase = [phase]
            winding_phases = [single_phase, single_phase]
            equipment = self.map_equipment(row, equipment_row, single_phase, buses, regulator_name)
            controllers = self.map_controllers(
                row, equipment_row, single_phase, buses[1], regulator_name
            )

            try:
                regulators.append(
                    DistributionRegulator.model_construct(
                        name=regulator_name,
                        buses=buses,
                        winding_phases=winding_phases,
                        equipment=equipment,
                        controllers=controllers,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to create DistributionRegulator {regulator_name}: {e}")

        used_sections.add(section_id)
        return regulators if regulators else None

    def map_name(self, row):
        return row["SectionID"]

    def map_buses(self, section):
        from_bus = self.system.get_component(
            component_type=DistributionBus,
            name=section["FromNodeID"],
        )
        to_bus = self.system.get_component(
            component_type=DistributionBus,
            name=section["ToNodeID"],
        )
        return [from_bus, to_bus]

    def map_phases(self, row, section):
        phase_str = str(row.get("PhaseON") or section.get("Phase") or "")
        phases = []
        if "A" in phase_str:
            phases.append(Phase.A)
        if "B" in phase_str:
            phases.append(Phase.B)
        if "C" in phase_str:
            phases.append(Phase.C)
        return phases

    def map_equipment(self, row, equipment_row, phases, buses, regulator_name):
        total_taps = int(float((equipment_row or {}).get("Taps", 32) or 32))
        max_buck = float(row.get("MaxBuck", (equipment_row or {}).get("MaxBuck", 10)) or 10)
        max_boost = float(row.get("MaxBoost", (equipment_row or {}).get("MaxBoost", 10)) or 10)
        kva = float((equipment_row or {}).get("KVA", 100) or 100)

        connection = self.map_connection_type(row)
        kv_ln = float((equipment_row or {}).get("KVLN", 0) or 0)
        if kv_ln > 0:
            winding_voltage = Voltage(kv_ln, "kilovolt")
            primary_voltage_type = VoltageTypes.LINE_TO_GROUND
            secondary_voltage_type = VoltageTypes.LINE_TO_GROUND
        else:
            winding_voltage = buses[1].rated_voltage
            primary_voltage_type = buses[0].voltage_type if buses[0].voltage_type else VoltageTypes.LINE_TO_LINE
            secondary_voltage_type = buses[1].voltage_type if buses[1].voltage_type else VoltageTypes.LINE_TO_LINE

        primary_taps = [
            self.map_tap_position(row, phase, total_taps, max_buck, max_boost) for phase in phases
        ]
        secondary_taps = [
            self.map_tap_position(row, phase, total_taps, max_buck, max_boost) for phase in phases
        ]

        min_tap_pu = 1 - max_buck / 100
        max_tap_pu = 1 + max_boost / 100

        windings = [
            WindingEquipment.model_construct(
                name=f"{row['SectionID']}_primary",
                resistance=0.1,
                is_grounded=connection == ConnectionType.STAR,
                rated_voltage=winding_voltage,
                voltage_type=primary_voltage_type,
                rated_power=ApparentPower(kva, "kilova"),
                num_phases=len(phases),
                connection_type=connection,
                tap_positions=primary_taps,
                total_taps=total_taps,
                min_tap_pu=min_tap_pu,
                max_tap_pu=max_tap_pu,
            ),
            WindingEquipment.model_construct(
                name=f"{row['SectionID']}_secondary",
                resistance=0.1,
                is_grounded=connection == ConnectionType.STAR,
                rated_voltage=winding_voltage,
                voltage_type=secondary_voltage_type,
                rated_power=ApparentPower(kva, "kilova"),
                num_phases=len(phases),
                connection_type=connection,
                tap_positions=secondary_taps,
                total_taps=total_taps,
                min_tap_pu=min_tap_pu,
                max_tap_pu=max_tap_pu,
            ),
        ]

        return DistributionTransformerEquipment.model_construct(
            name=f"{row.get('EqID', 'REGULATOR')}_{regulator_name}",
            pct_no_load_loss=0.0,
            pct_full_load_loss=0.0,
            windings=windings,
            coupling_sequences=[SequencePair(0, 1)],
            winding_reactances=[1.0],
            is_center_tapped=False,
        )

    def map_connection_type(self, row):
        connection_map = {
            0: ConnectionType.STAR,
            1: ConnectionType.STAR,
            2: ConnectionType.DELTA,
            3: ConnectionType.OPEN_DELTA,
            4: ConnectionType.DELTA,
        }
        connection_number = int(float(row.get("Conn", 0) or 0))
        return connection_map.get(connection_number, ConnectionType.STAR)

    def map_tap_position(self, row, phase, total_taps, max_buck, max_boost):
        suffix = self.map_phase_suffix(phase)
        raw_tap = float(row.get(f"Tap{suffix}", 0) or 0)

        # CYME regulator taps are positions around neutral (0). Convert to pu.
        half_taps = max(total_taps / 2, 1)
        step_up = (max_boost / 100) / half_taps
        step_down = (max_buck / 100) / half_taps
        if raw_tap >= 0:
            return 1 + raw_tap * step_up
        return 1 + raw_tap * step_down

    def map_controllers(self, row, equipment_row, phases, controlled_bus, regulator_name):
        max_step = int(max(float(row.get("MaxBuck", 0) or 0), float(row.get("MaxBoost", 0) or 0)))
        pt_ratio = float(row.get("PT", (equipment_row or {}).get("PT", 1)) or 1)
        ct_primary = float(row.get("CT", (equipment_row or {}).get("CT", 0)) or 0)
        is_reversible = bool(int(float(row.get("Reversible", (equipment_row or {}).get("Reversible", 0)) or 0)))

        controllers = []
        for phase in phases:
            suffix = self.map_phase_suffix(phase)
            v_setpoint = float(row.get(f"Vset{suffix}", row.get("VsetA", 120)) or 120)
            bandwidth = float(row.get(f"BandWidth{suffix}", row.get("BandWidthA", 2)) or 2)
            ldc_r = float(row.get(f"Rset{suffix}", 0) or 0)
            ldc_x = float(row.get(f"Xset{suffix}", 0) or 0)
            use_ldc = abs(ldc_r) > 0 or abs(ldc_x) > 0

            controllers.append(
                RegulatorController.model_construct(
                    name=f"{regulator_name}_{suffix}",
                    delay=Time(0, "seconds"),
                    v_setpoint=Voltage(v_setpoint, "volt"),
                    min_v_limit=Voltage(v_setpoint - bandwidth / 2, "volt"),
                    max_v_limit=Voltage(v_setpoint + bandwidth / 2, "volt"),
                    pt_ratio=pt_ratio,
                    use_ldc=use_ldc,
                    is_reversible=is_reversible,
                    ldc_R=Voltage(ldc_r, "volt"),
                    ldc_X=Voltage(ldc_x, "volt"),
                    ct_primary=Current(max(ct_primary, 0.0), "ampere"),
                    max_step=max_step,
                    bandwidth=Voltage(bandwidth, "volt"),
                    controlled_bus=controlled_bus,
                    controlled_phase=phase,
                )
            )

        return controllers

    def map_phase_suffix(self, phase):
        if phase == Phase.A:
            return "A"
        if phase == Phase.B:
            return "B"
        if phase == Phase.C:
            return "C"
        return "A"