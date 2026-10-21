from ditto.enumerations import OpenDSSFileTypes
from ditto.writers.opendss.equipment.sequence_impedance_branch_equipment import (
    SequenceImpedanceBranchEquipmentMapper,
)


class SequenceImpedanceSwitchEquipmentMapper(SequenceImpedanceBranchEquipmentMapper):
    opendss_file = OpenDSSFileTypes.SWITCH_CODES_FILE.value

    def map_controller(self):
        pass
