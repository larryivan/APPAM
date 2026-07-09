import unittest
from unittest.mock import patch

from app.services.job_runner import WorkflowExecutionTracker
from app.services.workflow_runtime import get_workflow_stage_definitions


class WorkflowExecutionTrackerTests(unittest.TestCase):
    def _tracker(self):
        return WorkflowExecutionTracker({
            'run_id': 'run-1',
            'workflow_id': 'appam-smk',
            'stages': get_workflow_stage_definitions('appam-smk'),
        })

    @patch('app.services.job_runner.append_workflow_run_event')
    @patch('app.services.job_runner.update_workflow_run')
    @patch('app.services.job_runner.update_workflow_stage')
    def test_interleaved_rules_do_not_complete_stages_early(
        self,
        update_stage,
        _update_run,
        append_event,
    ):
        tracker = self._tracker()

        tracker.handle_line('rule fastp_preprocess:')
        tracker.handle_line('rule megahit:')
        tracker.handle_line('rule fastp_preprocess:')

        statuses = [call.kwargs.get('status') for call in update_stage.call_args_list]
        self.assertEqual(statuses, ['running', 'running', 'running'])
        stage_started = [
            call for call in append_event.call_args_list
            if len(call.args) > 1 and call.args[1] == 'stage_started'
        ]
        self.assertEqual(len(stage_started), 2)

    @patch('app.services.job_runner.append_workflow_run_event')
    @patch('app.services.job_runner.update_workflow_run')
    @patch('app.services.job_runner.update_workflow_stage')
    def test_success_settles_seen_and_skipped_stages(
        self,
        update_stage,
        _update_run,
        _append_event,
    ):
        tracker = self._tracker()
        tracker.handle_line('rule fastp_preprocess:')
        update_stage.reset_mock()

        tracker.finalize('completed')

        states = {
            call.args[1]: call.kwargs['status']
            for call in update_stage.call_args_list
        }
        self.assertEqual(states['qc-trim'], 'completed')
        self.assertEqual(states['filter-contigs'], 'optional')
        self.assertEqual(states['assembly'], 'skipped')

    @patch('app.services.job_runner.append_workflow_run_event')
    @patch('app.services.job_runner.update_workflow_run')
    @patch('app.services.job_runner.update_workflow_stage')
    def test_failure_settles_other_seen_stages_as_interrupted(
        self,
        update_stage,
        _update_run,
        _append_event,
    ):
        tracker = self._tracker()
        tracker.handle_line('rule fastp_preprocess:')
        tracker.handle_line('rule megahit:')
        update_stage.reset_mock()

        tracker.finalize('failed', 'boom')

        states = {
            call.args[1]: call.kwargs['status']
            for call in update_stage.call_args_list
        }
        self.assertEqual(states['qc-trim'], 'interrupted')
        self.assertEqual(states['assembly'], 'failed')


if __name__ == '__main__':
    unittest.main()
