import math
import re
from collections import defaultdict

from gdm.distribution.enums import Phase
from gdm.distribution.components.distribution_feeder import DistributionFeeder
from gdm.distribution.components.distribution_substation import DistributionSubstation

_POS_MAP = {0: Phase.A, 1: Phase.B, 2: Phase.C, 3: Phase.N}
_PHASE_ORDER = {Phase.A: 0, Phase.B: 1, Phase.C: 2, Phase.N: 3}


def parse_phases(phase_str: str) -> list[Phase]:
    """Parse a Synergi positional phase string into GDM Phase values.

    Position 0 → A, 1 → B, 2 → C, 3 → N. A space means absent.
    Examples:
      "ABCN" → [A, B, C, N]
      " B N" → [B, N]
      "  C " → [C]
    """
    phases = []
    for i, char in enumerate(phase_str):
        if i in _POS_MAP and char.strip():
            phases.append(_POS_MAP[i])
    return phases


def phases_without_neutral(phases: list[Phase]) -> list[Phase]:
    return [p for p in phases if p != Phase.N]


def sort_phases(phases: list[Phase] | set[Phase]) -> list[Phase]:
    return sorted(phases, key=lambda p: _PHASE_ORDER.get(p, 99))


import re


def sanitize_name(name: str) -> str:
    name = str(name).strip()
    name = name.replace(" - ", "_")
    name = re.sub(r"[^\w.]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return default


def build_node_feeder_map(feeder_data, section_data) -> dict:
    """Build a mapping from node_id to feeder info for voltage and context lookups.

    Returns dict[node_id, {"feeder_id": str, "nominal_kvll": float, "sub_id": str}]
    """
    feeder_info = {}
    for _, row in feeder_data.iterrows():
        fid = str(row["FeederId"]).strip()
        nominal_kvll = safe_float(row.get("NominalKvll"), 12.47) or 12.47
        sub_id = str(row.get("SubstationId", "Unknown") or "Unknown").strip()
        feeder_info[fid] = {"nominal_kvll": nominal_kvll, "sub_id": sub_id}

    node_feeder_map: dict = {}
    for _, row in section_data.iterrows():
        fid = str(row.get("FeederId", "")).strip()
        from_node = str(row["FromNodeId"]).strip()
        to_node = str(row["ToNodeId"]).strip()
        if fid in feeder_info:
            info = {"feeder_id": fid, **feeder_info[fid]}
            node_feeder_map.setdefault(from_node, info)
            node_feeder_map.setdefault(to_node, info)

    return node_feeder_map


# Downloading mdbtools
import subprocess
import platform
import os
import tarfile
from urllib.request import urlretrieve
import sys
import pandas as pd

# Need to run:
# cp libmdb.so.2.0.1 libmdb.so.2
# cp libiconv.so.2.6.1 libiconv.so.2
# And repackage the tar file
def read_synergi_data(database_name, table_name):
    operating_system = platform.system()
    current_dir = os.path.realpath(os.path.dirname(__file__))
    if operating_system == "Windows":
        cmd = [os.path.join(current_dir, 'mdbtools', "mdb-export.exe"), database_name, table_name]
    else:    
        cmd = [os.path.join(current_dir, 'mdbtools','bin', "mdb-export"), database_name, table_name]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    return pd.read_csv(proc.stdout)


def download_mdbtools():
    current_dir = os.path.realpath(os.path.dirname(__file__))
    tar_file_name = os.path.join(current_dir, "mdbtools.tar.gz")
    mdb_dir = os.path.join(current_dir, "mdbtools")
    
    if platform.system() == "Windows":
        url = "https://github.com/kdheepak/mdbtools/releases/download/download/mdbtools-win.tar.gz"
    elif platform.system() == "Darwin":
        url = "https://github.com/kdheepak/mdbtools/releases/download/download/mdbtools-osx.tar.gz"
    else:
        url = "https://github.com/kdheepak/mdbtools/releases/download/download/mdbtools-linux.tar.gz"

    if os.path.exists(mdb_dir):
        print("mdbtools folder already exists. Skipping download")
        return
    print("Downloading mdbtools")
    urlretrieve(url, tar_file_name)
    print("Extracting mdbtools")
    with tarfile.open(tar_file_name) as tf:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tf, mdb_dir)
