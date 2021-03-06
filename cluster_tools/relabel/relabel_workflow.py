import os
import json
import luigi

from ..cluster_tasks import WorkflowBase
from . import find_uniques as unique_tasks
from . import find_labeling as labeling_tasks
from .. import write as write_tasks


class RelabelWorkflow(WorkflowBase):
    input_path = luigi.Parameter()
    input_key = luigi.Parameter()

    def requires(self):
        unique_task = getattr(unique_tasks,
                              self._get_task_name('FindUniques'))
        t1 = unique_task(tmp_folder=self.tmp_folder,
                         max_jobs=self.max_jobs,
                         config_dir=self.config_dir,
                         input_path=self.input_path,
                         input_key=self.input_key,
                         dependency=self.dependency)

        # for now, we hard-code the assignment path here,
        # because it is only used internally for this task
        # but it could also be exposed if this is useful
        # at some point
        assignment_path = os.path.join(self.tmp_folder, 'relabeling.pkl')
        labeling_task = getattr(labeling_tasks,
                                self._get_task_name('FindLabeling'))
        t2 = labeling_task(tmp_folder=self.tmp_folder,
                           max_jobs=self.max_jobs,
                           config_dir=self.config_dir,
                           input_path=self.input_path,
                           input_key=self.input_key,
                           assignment_path=assignment_path,
                           dependency=t1)

        write_task = getattr(write_tasks,
                             self._get_task_name('Write'))
        t3 = write_task(tmp_folder=self.tmp_folder,
                        max_jobs=self.max_jobs,
                        config_dir=self.config_dir,
                        input_path=self.input_path,
                        input_key=self.input_key,
                        output_path=self.input_path,
                        output_key=self.input_key,
                        assignment_path=assignment_path,
                        identifier='relabel',
                        dependency=t2)
        return t3

    @staticmethod
    def get_config():
        configs = super(RelabelWorkflow, RelabelWorkflow).get_config()
        configs.update({'find_uniques':
                        unique_tasks.FindUniquesLocal.default_task_config(),
                        'find_labeling':
                        labeling_tasks.FindLabelingLocal.default_task_config(),
                        'write':
                        write_tasks.WriteLocal.default_task_config()})
        return configs
