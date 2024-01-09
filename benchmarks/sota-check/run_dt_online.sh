#!/bin/bash

#SBATCH --job-name=dt_online
#SBATCH --ntasks=32
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --output=dt_online_output_%j.txt
#SBATCH --error=dt_online_error_%j.txt

python ../../examples/dt/dt_online.py
