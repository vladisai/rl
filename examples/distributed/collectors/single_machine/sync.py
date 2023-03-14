# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Distributed synchronous data collection on a single node.

The default configuration works fine on machines equipped with 4 GPUs, but can
be scaled up or down depending on the available configuration.

The number of nodes should not be greater than the number of GPUs minus 1, as
each node will be assigned one GPU to work with, while the main worker will
keep its own GPU (presumably for model training).

Each node can support multiple workers through the usage of `ParallelEnv`.

The default task is `Pong-v5` but a different one can be picked through the
`--env` flag. Any available gym env will work.

"""
from argparse import ArgumentParser

import torch
import tqdm

from torchrl.collectors.collectors import RandomPolicy, SyncDataCollector
from torchrl.collectors.distributed import DistributedSyncDataCollector
from torchrl.envs import EnvCreator, ParallelEnv
from torchrl.envs.libs.gym import GymEnv

parser = ArgumentParser()
parser.add_argument(
    "--num_workers", default=8, type=int, help="Number of workers in each node."
)
parser.add_argument(
    "--num_nodes", default=4, type=int, help="Number of nodes for the collector."
)
parser.add_argument(
    "--frames_per_batch",
    default=800,
    type=int,
    help="Number of frames in each batch of data. Must be "
    "divisible by the product of nodes and workers.",
)
parser.add_argument(
    "--total_frames",
    default=1_200_000,
    type=int,
    help="Total number of frames collected by the collector. Must be "
    "divisible by the product of nodes and workers.",
)
parser.add_argument(
    "--backend",
    default="nccl",
    help="backend for torch.distributed. Must be one of "
    "'gloo', 'nccl' or 'mpi'. Use 'nccl' for cuda to cuda "
    "data passing.",
)
parser.add_argument(
    "--env",
    default="ALE/Pong-v5",
    help="Gym environment to be run.",
)
if __name__ == "__main__":
    args = parser.parse_args()
    num_workers = args.num_workers
    num_nodes = args.num_nodes
    frames_per_batch = args.frames_per_batch
    launcher = "mp"

    device_count = torch.cuda.device_count()

    if args.backend == "nccl":
        if num_nodes > device_count - 1:
            raise RuntimeError(
                "Expected at most as many workers as GPU devices (excluded cuda:0 which "
                f"will be used by the main worker). Got {num_workers} workers for {device_count} GPUs."
            )
        collector_kwargs = [
            {"device": f"cuda:{i}", "storing_device": f"cuda:{i}"}
            for i in range(1, num_nodes + 2)
        ]
    elif args.backend == "gloo":
        collector_kwargs = {"device": "cpu", "storing_device": "cpu"}
    else:
        raise NotImplementedError(
            f"device assignment not implemented for backend {args.backend}"
        )

    make_env = EnvCreator(lambda: GymEnv(args.env))
    if num_workers == 1:
        action_spec = make_env().action_spec
    else:
        make_env = ParallelEnv(num_workers, make_env)
        action_spec = make_env.action_spec

    collector = DistributedSyncDataCollector(
        [make_env] * num_nodes,
        RandomPolicy(action_spec),
        num_workers_per_collector=num_workers,
        frames_per_batch=frames_per_batch,
        total_frames=args.total_frames,
        collector_class=SyncDataCollector,
        collector_kwargs=collector_kwargs,
        storing_device="cuda:0" if args.backend == "nccl" else "cpu",
        launcher=launcher,
        backend=args.backend,
    )

    pbar = tqdm.tqdm(total=collector.total_frames)
    for data in collector:
        pbar.update(data.numel())
        pbar.set_description(f"data shape: {data.shape}, data device: {data.device}")
    collector.shutdown()
    exit()
