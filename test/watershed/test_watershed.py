#! /g/kreshuk/pape/Work/software/conda/miniconda3/envs/cluster_env/bin/python

import os
import sys
import luigi

import h5py
import z5py

try:
    from cluster_tools.watershed import WatershedWorkflow
except ImportError:
    sys.path.append('../..')
    from cluster_tools.watershed import WatershedWorkflow


def test_ws():
    # input_path = '/home/cpape/Work/data/isbi2012/isbi_train_offsetsV4_3d_meantda_damws2deval_final.h5'
    input_path = '/g/kreshuk/data/isbi2012_challenge/predictions/isbi2012_train_affinities.h5'
    input_key = output_key = 'data'
    output_path = './ws.n5'

    max_jobs = 8

    ret = luigi.build([WatershedWorkflow(input_path=input_path, input_key=input_key,
                                         output_path=output_path, output_key=output_key,
                                         config_dir='./configs',
                                         tmp_folder='./tmp',
                                         target='slurm',
                                         max_jobs=max_jobs)], local_scheduler=True)
    if ret:
        from cremi_tools.viewer.volumina import view
        assert os.path.exists(os.path.exists(output_path))
        with h5py.File(input_path) as f:
            affs = f['data'][:3].transpose((1, 2, 3, 0))
        ws = z5py.File(output_path)['data'][:]
        view([affs, ws])


if __name__ == '__main__':
    test_ws()