import tempfile
import numpy as np
from pathlib import Path
from ditto.readers.opendss.reader import Reader
from ditto.writers.opendss.write import Writer
from tests.helpers import get_metrics

master_dss_path = Path(
    "/Users/alatif/Documents/GitHub/ditto/tests/data/opendss_circuit_models/P4U/Master.dss"
)

# Create a temporary directory
with tempfile.TemporaryDirectory() as temp_dir:
    # 1. Read the OpenDSS model
    reader = Reader(Opendss_master_file=master_dss_path)
    reader.parse()
    model = reader.model

    # 2. Compute pre-metrics
    pre_metrics = get_metrics(model)

    # 3. Write the model back to the temp directory
    writer = Writer(output_path=temp_dir)
    writer.write(model)

    # 4. Read the model back from the written output
    # OpenDSS writer creates a Master.dss in the output_path
    new_master_dss = Path(temp_dir) / "Master.dss"
    reader_post = Reader(Opendss_master_file=new_master_dss)
    reader_post.parse()
    model_post = reader_post.model

    # 5. Compute post-metrics
    post_metrics = get_metrics(model_post)

    # 6. Compare and print
    print(
        f"{'Metric':<30} | {'Pre':<10} | {'Post':<10} | {'Abs Diff':<10} | {'Rel Diff':<10} | {'IsClose'}"
    )
    print("-" * 100)

    all_keys = sorted(set(pre_metrics.keys()) | set(post_metrics.keys()))

    for key in all_keys:
        pre_val = pre_metrics.get(key, 0)
        post_val = post_metrics.get(key, 0)

        abs_diff = abs(pre_val - post_val)
        rel_diff = abs_diff / (abs(pre_val) + 1e-12)

        is_close = bool(np.isclose(pre_val, post_val, rtol=0.01, atol=0.01))

        print(
            f"{key:<30} | {pre_val:<10.4f} | {post_val:<10.4f} | {abs_diff:<10.4f} | {rel_diff:<10.4f} | {is_close}"
        )
