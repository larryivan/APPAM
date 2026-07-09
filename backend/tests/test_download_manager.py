import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import database
from app.services import download_manager
from app.services.download_store import get_download_task


class DownloadManagerTests(unittest.TestCase):
    def setUp(self):
        self.database_dir = tempfile.TemporaryDirectory()
        self.database_patch = mock.patch.object(
            database,
            'DATABASE_FILE',
            str(Path(self.database_dir.name) / 'downloads.db'),
        )
        self.database_patch.start()
        database.init_db()
        conn = database.get_db_connection()
        try:
            conn.execute("INSERT INTO projects (id, name) VALUES ('project-1', 'Download tests')")
            conn.commit()
        finally:
            conn.close()
        download_manager.download_tasks.clear()
        download_manager.download_threads.clear()

    def tearDown(self):
        download_manager.download_tasks.clear()
        download_manager.download_threads.clear()
        self.database_patch.stop()
        self.database_dir.cleanup()

    def _task(self, root: Path):
        task = download_manager.DownloadTask(
            'task-1',
            'https://example.org/reads.fastq.gz',
            'reads.fastq.gz',
            'project-1',
            '.',
            False,
        )
        task.destination_path = str(root / 'reads.fastq.gz')
        task.file_path = str(root / '.reads.fastq.gz.part')
        return task

    def test_worker_promotes_completed_temporary_file_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task = self._task(root)

            def fake_download(active_task):
                Path(active_task.file_path).write_bytes(b'complete-data')
                active_task.downloaded_size = len(b'complete-data')
                active_task.total_size = len(b'complete-data')
                active_task.status = 'completed'

            with mock.patch.object(download_manager, 'single_thread_download', fake_download):
                download_manager.download_worker(task)

            self.assertEqual(task.status, 'completed')
            self.assertEqual(Path(task.destination_path).read_bytes(), b'complete-data')
            self.assertFalse(Path(task.file_path).exists())
            self.assertEqual(get_download_task(task.task_id)['status'], 'completed')

    def test_failed_download_does_not_replace_existing_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task = self._task(root)
            Path(task.destination_path).write_bytes(b'original')

            def fake_download(active_task):
                Path(active_task.file_path).write_bytes(b'partial')
                active_task.status = 'error'
                active_task.error = 'network failure'

            with mock.patch.object(download_manager, 'single_thread_download', fake_download):
                download_manager.download_worker(task)

            self.assertEqual(task.status, 'error')
            self.assertEqual(Path(task.destination_path).read_bytes(), b'original')

    def test_cleanup_removes_failed_partial_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task = self._task(Path(temp_dir))
            Path(task.file_path).write_bytes(b'partial')
            task.status = 'error'
            download_manager.download_tasks[task.task_id] = task

            removed = download_manager.cleanup_completed_downloads('project-1')

            self.assertEqual(removed, 1)
            self.assertFalse(Path(task.file_path).exists())

    def test_restore_pauses_interrupted_download_and_keeps_partial_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task = self._task(Path(temp_dir))
            Path(task.file_path).write_bytes(b'partial-data')
            task.status = 'downloading'
            task.total_size = 100
            download_manager._persist_task(task, force=True, strict=True)
            download_manager.download_tasks.clear()

            restored = download_manager.restore_download_tasks()

            self.assertEqual(restored, 1)
            restored_task = download_manager.download_tasks[task.task_id]
            self.assertEqual(restored_task.status, 'paused')
            self.assertEqual(restored_task.downloaded_size, len(b'partial-data'))
            self.assertEqual(get_download_task(task.task_id)['status'], 'paused')

    def test_cleanup_deletes_persisted_terminal_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task = self._task(Path(temp_dir))
            task.status = 'error'
            task.error = 'network failed'
            download_manager.download_tasks[task.task_id] = task
            download_manager._persist_task(task, force=True, strict=True)

            removed = download_manager.cleanup_completed_downloads('project-1')

            self.assertEqual(removed, 1)
            self.assertIsNone(get_download_task(task.task_id))


if __name__ == '__main__':
    unittest.main()
