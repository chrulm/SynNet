"""Common methods and params shared by all models.
"""

from typing import Union

import numpy as np
import torch
from scipy import sparse


def get_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", type=str, default="data/featurized/Xy", help="Directory with X,y data."
    )
    parser.add_argument(
        "-f", "--featurize", type=str, default="fp", help="Choose from ['fp', 'gin']"
    )
    parser.add_argument(
        "-r", "--rxn_template", type=str, default="hb", help="Choose from ['hb', 'pis']"
    )
    parser.add_argument("--radius", type=int, default=2, help="Radius for Morgan fingerprint.")
    parser.add_argument(
        "--nbits", type=int, default=4096, help="Number of Bits for Morgan fingerprint."
    )
    parser.add_argument("--out_dim", type=int, default=256, help="Output dimension.")
    parser.add_argument("--ncpu", type=int, default=16, help="Number of cpus")
    parser.add_argument("--batch_size", type=int, default=64, help="Batch size")
    parser.add_argument("--epoch", type=int, default=2000, help="Maximum number of epoches.")
    parser.add_argument(
        "--ckpt-file",
        type=str,
        default=None,
        help="Checkpoint file. If provided, load and resume training.",
    )
    parser.add_argument("-v", "--version", type=int, default=1, help="Version")
    parser.add_argument("--debug", default=False, action="store_true")
    parser.add_argument("--fast-dev-run", default=False, action="store_true")
    return parser.parse_args()


def xy_to_dataloader(
    X_file: str, y_file: str, task: str = "regression", n: Union[int, float] = 1.0, **kwargs
):
    """Loads featurized X,y `*.npz`-data into a `DataLoader`"""
    X = sparse.load_npz(X_file)
    y = sparse.load_npz(y_file)
    # Filer?
    if isinstance(n, int):
        n = min(n, X.shape[0])  # ensure n does not exceed size of dataset
        X = X[:n]
        y = y[:n]
    elif isinstance(n, float) and n < 1.0:
        xn = X.shape[0] * n
        yn = X.shape[0] * n
        X = X[:xn]
        y = y[:yn]
    else:
        pass  #
    X = np.atleast_2d(np.asarray(X.todense()))
    y = (
        np.atleast_2d(np.asarray(y.todense()))
        if task == "regression"
        else np.asarray(y.todense()).squeeze()
    )
    dataset = torch.utils.data.TensorDataset(
        torch.Tensor(X),
        torch.Tensor(y),
    )
    return torch.utils.data.DataLoader(dataset, **kwargs)


if __name__ == "__main__":
    import json

    args = get_args()
    print("Default Arguments are:")
    print(json.dumps(args.__dict__, indent=2))