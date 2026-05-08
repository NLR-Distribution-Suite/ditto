from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_vsource import DistributionVoltageSource
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.distribution.equipment.voltagesource_equipment import VoltageSourceEquipment
from gdm.distribution.equipment.phase_voltagesource_equipment import PhaseVoltageSourceEquipment
from gdm.quantities import Reactance
from infrasys.quantities import Voltage, Resistance, Angle
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import sanitize_name, safe_float
from loguru import logger

_DEFAULT_V_PU = 1.02  # Synergi treats 120V on 120V base as "unset"; use 1.02 pu


class DistributionVoltageSourceMapper(SynergiMapper):

    synergi_table = "InstFeeders"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        feeder_id = str(row["FeederId"]).strip()

        head_node_id = self.map_head_node(feeder_id, section_id_sections)
        if head_node_id is None:
            logger.warning(f"VSource {feeder_id}: no head node found, skipping")
            return None

        bus = self.map_bus(head_node_id)
        if bus is None:
            return None

        feeder, substation = self._lookup_feeder_substation(head_node_id)
        equipment = self.map_equipment(row, feeder_id)

        return DistributionVoltageSource(
            name=sanitize_name(f"vsource_{feeder_id}"),
            bus=bus,
            phases=[Phase.A, Phase.B, Phase.C],
            equipment=equipment,
            substation=substation,
            feeder=feeder,
        )

    def map_head_node(self, feeder_id, section_id_sections):
        """Return the physical source bus node ID for this feeder.

        Mirrors synergi_converter's FeederTopology._find_head_node():
        1. If the feeder name itself is a virtual head node (appears as FromNodeId
           but never as ToNodeId), the source bus is its one downstream neighbour.
        2. Single candidate -> use it directly.
        3. Multiple candidates -> pick by most outgoing sections.
        """
        feeder_sections = [
            s for s in section_id_sections.values()
            if str(s.get("FeederId", "")).strip() == feeder_id
        ]
        from_ids = {str(s["FromNodeId"]).strip() for s in feeder_sections}
        to_ids = {str(s["ToNodeId"]).strip() for s in feeder_sections}
        candidates = from_ids - to_ids
        if not candidates:
            return None

        # Case 1: feeder name is a virtual head node
        if feeder_id in candidates:
            for s in feeder_sections:
                if str(s["FromNodeId"]).strip() == feeder_id:
                    return str(s["ToNodeId"]).strip()

        # Case 2: single physical candidate
        if len(candidates) == 1:
            return next(iter(candidates))

        # Case 3: multiple candidates — pick most connected
        from_count = {n: sum(1 for s in feeder_sections if str(s["FromNodeId"]).strip() == n)
                      for n in candidates}
        best = max(from_count, key=from_count.get)
        logger.warning(f"Feeder {feeder_id}: {len(candidates)} head candidates, chose {best!r}")
        return best

    def map_bus(self, head_node_id):
        bus_name = sanitize_name(head_node_id)
        try:
            return self.system.get_component(DistributionBus, bus_name)
        except Exception:
            logger.warning(f"VSource: head bus {bus_name!r} not found, skipping")
            return None

    def map_equipment(self, row, feeder_id):
        nominal_kvll = safe_float(row.get("NominalKvll"), 12.47)
        r1 = safe_float(row.get("PosSequenceResistance"), 0.1)
        x1 = safe_float(row.get("PosSequenceReactance"), 0.5)
        r0 = safe_float(row.get("ZeroSequenceResistance"), r1)
        x0 = safe_float(row.get("ZeroSequenceReactance"), x1)

        raw = [
            (Phase.A, safe_float(row.get("ByPhVoltLevelPh1"), 120.0), safe_float(row.get("ByPhVoltDegPh1"), 0.0)),
            (Phase.B, safe_float(row.get("ByPhVoltLevelPh2"), 120.0), safe_float(row.get("ByPhVoltDegPh2"), -120.0)),
            (Phase.C, safe_float(row.get("ByPhVoltLevelPh3"), 120.0), safe_float(row.get("ByPhVoltDegPh3"), 120.0)),
        ]

        phase_sources = []
        for phase, v120, angle in raw:
            v_pu = _DEFAULT_V_PU if v120 == 120.0 else v120 / 120.0
            phase_sources.append(PhaseVoltageSourceEquipment(
                name=sanitize_name(f"vsrc_{feeder_id}_{phase.value}"),
                r1=Resistance(r1, "ohm"),
                x1=Reactance(x1, "ohm"),
                r0=Resistance(r0, "ohm"),
                x0=Reactance(x0, "ohm"),
                voltage=Voltage(nominal_kvll * v_pu, "kilovolt"),
                voltage_type=VoltageTypes.LINE_TO_LINE,
                angle=Angle(angle, "degree"),
            ))

        return VoltageSourceEquipment(
            name=sanitize_name(f"vsrc_equip_{feeder_id}"),
            sources=phase_sources,
        )
