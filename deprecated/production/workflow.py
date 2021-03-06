import json
import os
import luigi

from .components import ComponentsWorkflow
from .watershed import FillingWatershedTask, Watershed2dTask
from .relabel import RelabelWorkflow
from .stitching import ConsensusStitchingWorkflow
from .evaluation import SkeletonEvaluationTask
from .util import make_dirs
from .blockwise_multicut import BlockwiseMulticutWorkflow
from .multicut import MulticutTask
from .write import WriteAssignmentTask
# from .util import DummyTask


class WatershedWorkflow(luigi.Task):
    # path to the n5 file and keys
    path = luigi.Parameter()
    aff_key = luigi.Parameter()
    mask_key = luigi.Parameter()
    ws_key = luigi.Parameter()
    # maximal number of jobs that will be run in parallel
    max_jobs = luigi.IntParameter()
    # path to the configuration
    # TODO allow individual paths for individual blocks
    config_path = luigi.Parameter()
    tmp_folder = luigi.Parameter()
    # for evaluation
    # FIXME default does not work; this still needs to be specified
    # TODO different time estimates for different sub-tasks
    time_estimate = luigi.IntParameter(default=10)
    run_local = luigi.BoolParameter(default=False)

    def requires(self):
        # make the tmp, log and err dicts if necessary
        make_dirs(self.tmp_folder)

        components_task = ComponentsWorkflow(path=self.path, aff_key=self.aff_key,
                                             mask_key=self.mask_key, out_key=self.ws_key,
                                             max_jobs=self.max_jobs,
                                             config_path=self.config_path,
                                             tmp_folder=self.tmp_folder,
                                             time_estimate=self.time_estimate,
                                             run_local=self.run_local)
        ws_task = FillingWatershedTask(path=self.path, aff_key=self.aff_key,
                                       seeds_key=self.ws_key, mask_key=self.mask_key,
                                       max_jobs=self.max_jobs, config_path=self.config_path,
                                       tmp_folder=self.tmp_folder,
                                       dependency=components_task,
                                       time_estimate=self.time_estimate,
                                       run_local=self.run_local)
        relabel_task = RelabelWorkflow(path=self.path, key=self.ws_key,
                                       max_jobs=self.max_jobs,
                                       config_path=self.config_path,
                                       tmp_folder=self.tmp_folder,
                                       dependency=ws_task,
                                       time_estimate=self.time_estimate,
                                       run_local=self.run_local)
        return relabel_task

    # dummy run and output
    def run(self):
        out_path = self.input().path
        assert os.path.exists(out_path)
        res_file = self.output().path
        with open(res_file, 'w') as f:
            f.write('Success')

    def output(self):
        out_path = os.path.join(self.tmp_folder, 'watershed_workflow.log')
        return luigi.LocalTarget(out_path)


class Watersehd2dWorkflow(luigi.Task):

    # path to the n5 file and keys
    path = luigi.Parameter()
    aff_key = luigi.Parameter()
    mask_key = luigi.Parameter()
    ws_key = luigi.Parameter()
    # maximal number of jobs that will be run in parallel
    max_jobs = luigi.IntParameter()
    # path to the configuration
    # TODO allow individual paths for individual blocks
    config_path = luigi.Parameter()
    tmp_folder = luigi.Parameter()
    # FIXME default does not work; this still needs to be specified
    # TODO different time estimates for different sub-tasks
    time_estimate = luigi.IntParameter(default=10)
    run_local = luigi.BoolParameter(default=False)

    def requires(self):
        # make the tmp, log and err dicts if necessary
        make_dirs(self.tmp_folder)

        ws_task = Watershed2dTask(path=self.path, aff_key=self.aff_key,
                                  out_key=self.ws_key, mask_key=self.mask_key,
                                  max_jobs=self.max_jobs, config_path=self.config_path,
                                  tmp_folder=self.tmp_folder,
                                  time_estimate=self.time_estimate,
                                  run_local=self.run_local)
        # return ws_task
        relabel_task = RelabelWorkflow(path=self.path, key=self.ws_key,
                                       max_jobs=self.max_jobs, config_path=self.config_path,
                                       tmp_folder=self.tmp_folder,
                                       dependency=ws_task,
                                       time_estimate=self.time_estimate,
                                       run_local=self.run_local)
        return relabel_task

    # dummy run and output
    def run(self):
        out_path = self.input().path
        assert os.path.exists(out_path)
        res_file = self.output().path
        with open(res_file, 'w') as f:
            f.write('Success')

    def output(self):
        out_path = os.path.join(self.tmp_folder, 'watershed_2d_workflow.log')
        return luigi.LocalTarget(out_path)


class SegmentationWorkflow(luigi.WrapperTask):

    # path to the n5 file and keys
    path = luigi.Parameter()
    aff_key = luigi.Parameter()
    mask_key = luigi.Parameter()
    ws_key = luigi.Parameter()
    node_labeling_key = luigi.Parameter()
    seg_key = luigi.Parameter()
    # maximal number of jobs that will be run in parallel
    max_jobs = luigi.IntParameter()
    # path to the configuration
    config_path = luigi.Parameter()
    tmp_folder_ws = luigi.Parameter()
    tmp_folder_seg = luigi.Parameter()
    # for evaluation
    skeleton_keys = luigi.ListParameter(default=[])
    # FIXME default does not work; this still needs to be specified
    # TODO different time estimates for different sub-tasks
    time_estimate = luigi.IntParameter(default=10)
    run_local = luigi.BoolParameter(default=False)

    def requires(self):
        # make the tmp, log and err dicts if necessary
        make_dirs(self.tmp_folder_ws)
        make_dirs(self.tmp_folder_seg)

        # get the tasks for watershed and stitching from the config
        with open(self.config_path) as f:
            config = json.load(f)
            ws_task_key = config.get('ws_task', 'ws')
            stitch_task_key = config.get('stitch_task', 'consensus_stitching')
            n_jobs_write = config.get('n_jobs_write', 50)

        ws_task_dict = {'ws': WatershedWorkflow,
                        'ws_2d': Watersehd2dWorkflow}
        assert ws_task_key in ws_task_dict, ws_task_key
        ws = ws_task_dict[ws_task_key]

        stitch_task_dict = {'consensus_stitching': ConsensusStitchingWorkflow,
                            'multicut': MulticutTask,
                            'blockwise_multicut': BlockwiseMulticutWorkflow}
        assert stitch_task_key in stitch_task_dict
        stitch = stitch_task_dict[stitch_task_key]

        ws_task = ws(path=self.path,
                     aff_key=self.aff_key,
                     mask_key=self.mask_key,
                     ws_key=self.ws_key,
                     max_jobs=self.max_jobs,
                     config_path=self.config_path,
                     tmp_folder=self.tmp_folder_ws,
                     time_estimate=self.time_estimate,
                     run_local=self.run_local)
        stitch_task = stitch(path=self.path,
                             aff_key=self.aff_key,
                             ws_key=self.ws_key,
                             out_key=self.node_labeling_key,
                             max_jobs=self.max_jobs,
                             config_path=self.config_path,
                             tmp_folder=self.tmp_folder_seg,
                             dependency=ws_task,
                             time_estimate=self.time_estimate,
                             run_local=self.run_local)
        write_task = WriteAssignmentTask(path=self.path,
                                         in_key=self.ws_key,
                                         out_key=self.seg_key,
                                         config_path=self.config_path,
                                         max_jobs=n_jobs_write,
                                         tmp_folder=self.tmp_folder_seg,
                                         identifier='write_' + ws_task_key + '_' + stitch_task_key,
                                         dependency=stitch_task,
                                         time_estimate=self.time_estimate,
                                         run_local=self.run_local)

        if self.skeleton_keys:
            with open(self.config_path) as f:
                n_threads = json.load(f)['n_threads']
            eval_task = SkeletonEvaluationTask(path=self.path,
                                               seg_key=self.seg_key,
                                               skeleton_keys=self.skeleton_keys,
                                               n_threads=n_threads,
                                               tmp_folder=self.tmp_folder_seg,
                                               dependency=write_task,
                                               time_estimate=self.time_estimate,
                                               run_local=self.run_local)
            return eval_task
        #
        else:
            return write_task


def write_default_config(path,
                         ws_task='ws',
                         stitch_task='consensus_stitching',
                         # parameters for block shapes / shifts and chunks
                         block_shape=[50, 512, 512],
                         chunks=[25, 256, 256],
                         block_shape2=[75, 768, 768],
                         block_shift=[37, 384, 385],
                         # parameters for affinities used for components
                         boundary_threshold=.05,
                         aff_slices=[[0, 12], [12, 13]],
                         invert_channels=[True, False],
                         # parameters for watershed
                         boundary_threshold2=.2,
                         sigma_maxima=2.0,
                         size_filter=25,
                         # parameters for consensus stitching
                         weight_merge_edges=False,
                         weight_multicut_edges=False,
                         weighting_exponent=1.,
                         merge_threshold=.8,
                         affinity_offsets=[[-1, 0, 0],
                                           [0, -1, 0],
                                           [0, 0, -1]],
                         # parameter for lifted multicut in consensus stitching
                         # (by default rf os set to None, which means lmc is not used)
                         use_lmc=False,
                         rf_path=None,
                         lifted_nh=2,
                         # general parameter
                         n_threads=16,
                         # roi to process only subparts of the volume
                         roi=None):
    """
    Write the minimal config for consensus stitching workflow
    """
    try:
        with open(path) as f:
            config = json.load(f)
    except Exception:
        config = {}

    if rf_path is not None:
        assert isinstance(rf_path, (list, tuple))
        assert all(os.path.exists(rfp) for rfp in rf_path)

    assert ws_task in ('ws', 'ws_2d'), ws_task
    assert stitch_task in ('consensus_stitching', 'multicut',
                           'blockwise_multicut'), stitch_task

    config.update({'ws_task': ws_task,
                   'stitch_task': stitch_task,
                   'block_shape': block_shape,
                   'block_shape2': block_shape2,
                   'block_shift': block_shift,
                   'chunks': chunks,
                   'boundary_threshold': boundary_threshold,
                   'aff_slices': aff_slices,
                   'invert_channels': invert_channels,
                   'boundary_threshold2': boundary_threshold2,
                   'sigma_maxima': sigma_maxima,
                   'size_filter': size_filter,
                   'weight_merge_edges': weight_merge_edges,
                   'weight_multicut_edges': weight_multicut_edges,
                   'weighting_exponent': weighting_exponent,
                   'merge_threshold': merge_threshold,
                   'affinity_offsets': affinity_offsets,
                   'use_lmc': use_lmc,
                   'rf_path': rf_path,
                   'lifted_nh': lifted_nh,
                   'n_threads': n_threads})
    if roi is not None:
        assert len(roi) == 2
        assert len(roi[0]) == len(roi[1]) == 3
        config['roi'] = roi
    with open(path, 'w') as f:
        json.dump(config, f)


def write_dt_components_config(path,
                               # parameters for affinities used for components
                               # (defaults are different than for the thresholding based variant)
                               boundary_threshold=.2,
                               aff_slices=[[0, 3], [12, 13]],
                               invert_channels=[True, False],
                               resolution=(40., 4., 4.),
                               distance_threshold=40,
                               sigma=0.):
    """
    Write config to run the dt components workflow.
    Assumes that a default config already exits (otherwise writes it)
    """
    try:
        with open(path) as f:
            config = json.load(f)
    except Exception:
        write_default_config(path)
        with open(path) as f:
            config = json.load(f)

    config.update({'boundary_threshold': boundary_threshold,
                   'aff_slices': aff_slices,
                   'invert_channels': invert_channels,
                   'resolution': resolution,
                   'distance_threshold': distance_threshold,
                   'sigma': sigma})
    with open(path, 'w') as f:
        json.dump(config, f)


# write additional config, e.g. for salvage runs
def write_additional_config(path, **additional_config):
    assert os.path.isfile(path), path
    with open(path) as f:
        config = json.load(f)
    config.update(**additional_config)
    with open(path, 'w') as f:
        json.dump(config, f)
