from collections import defaultdict

from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import sanitize_name
from gdm.distribution.components.distribution_feeder import DistributionFeeder
from gdm.distribution.components.distribution_substation import DistributionSubstation


class DistributionSubstationMapper(SynergiMapper):

    synergi_table = "InstFeeders"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        # Substations need all their feeders at once — use parse_all() instead.
        return None

    def parse_all(self, table_data, unit_type, section_id_sections, from_node_sections, to_node_sections):
        """Create DistributionSubstation objects grouped by SubstationId."""
        sub_feeders: dict[str, list[DistributionFeeder]] = defaultdict(list)

        for _, row in table_data.iterrows():
            fid = sanitize_name(str(row["FeederId"]).strip())
            sub_id = str(row.get("SubstationId", "Unknown") or "Unknown").strip()
            try:
                feeder = self.system.get_component(DistributionFeeder, name=fid)
                sub_feeders[sub_id].append(feeder)
            except Exception:
                pass

        return [
            DistributionSubstation(name=sanitize_name(sub_id), feeders=feeders)
            for sub_id, feeders in sub_feeders.items()
        ]
