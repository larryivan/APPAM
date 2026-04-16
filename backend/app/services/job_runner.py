import os
import json
import socket
import subprocess
import time
import signal
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

try:
    import select
except ImportError:  # pragma: no cover - Windows fallback
    select = None

from .job_store import (
    append_workflow_run_event,
    attach_process_info,
    get_job,
    is_cancel_requested,
    load_workflow_manifest,
    mark_job_finished,
    mark_job_started,
    replace_workflow_artifacts,
    update_job_heartbeat,
    update_workflow_run,
    update_workflow_stage,
)
from .workflow_runtime import detect_rule_name, get_rule_to_stage_map


def _backend_dir() -> str:
    return os.getenv(
        'APPAM_BACKEND_DIR',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    )


def _now_str() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')


def _ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_log_line(log_file, line: str) -> None:
    log_file.write(line)
    if not line.endswith('\n'):
        log_file.write('\n')
    log_file.flush()


def _terminate_process(process: subprocess.Popen, log_file) -> None:
    if os.name != 'nt':
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            process.terminate()
    else:
        process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except Exception:
                process.kill()
        else:
            process.kill()


class WorkflowExecutionTracker:
    def __init__(self, workflow_context: dict | None):
        workflow_context = workflow_context or {}
        self.run_id = workflow_context.get('run_id')
        self.workflow_id = workflow_context.get('workflow_id')
        self.stages = workflow_context.get('stages') or []
        self.stage_lookup = {stage['id']: stage for stage in self.stages}
        self.rule_to_stage = get_rule_to_stage_map(self.workflow_id) if self.workflow_id else {}
        self.seen_stage_ids: list[str] = []
        self.seen_rules: dict[str, set[str]] = {stage['id']: set() for stage in self.stages}
        self.current_stage_id: str | None = None
        self.current_rule: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.run_id and self.workflow_id and self.stages)

    def handle_line(self, line: str) -> None:
        if not self.enabled:
            return
        rule_name = detect_rule_name(line)
        if not rule_name:
            return
        stage = self.rule_to_stage.get(rule_name)
        if not stage:
            return

        if self.current_stage_id and self.current_stage_id != stage['id']:
            self._mark_stage_completed(self.current_stage_id)

        if self.current_stage_id != stage['id']:
            self.current_stage_id = stage['id']
            if stage['id'] not in self.seen_stage_ids:
                self.seen_stage_ids.append(stage['id'])
            append_workflow_run_event(
                self.run_id,
                'stage_started',
                stage_id=stage['id'],
                message=f"Stage started: {stage['title']}",
            )

        seen = self.seen_rules.setdefault(stage['id'], set())
        seen.add(rule_name)
        self.current_rule = rule_name
        started_at = _now_str()
        total_rules = len(stage.get('rules', []))
        completed_rules = max(0, min(len(seen) - 1, total_rules))

        update_workflow_run(
            self.run_id,
            current_stage_id=stage['id'],
            current_stage_title=stage['title'],
            current_rule=rule_name,
            status='running',
        )
        update_workflow_stage(
            self.run_id,
            stage['id'],
            status='running',
            started_at=started_at,
            current_rule=rule_name,
            completed_rules=completed_rules,
            total_rules=total_rules,
        )
        append_workflow_run_event(
            self.run_id,
            'rule_started',
            stage_id=stage['id'],
            rule_name=rule_name,
            message=f'Rule started: {rule_name}',
        )

    def finalize(self, final_status: str, error_message: str | None = None) -> None:
        if not self.enabled:
            return

        finished_at = _now_str()
        if self.current_stage_id:
            stage = self.stage_lookup.get(self.current_stage_id)
            if stage:
                if final_status == 'completed':
                    self._mark_stage_completed(self.current_stage_id, finished_at=finished_at)
                else:
                    update_workflow_stage(
                        self.run_id,
                        self.current_stage_id,
                        status=final_status,
                        finished_at=finished_at,
                        current_rule=None,
                    )
        update_workflow_run(
            self.run_id,
            current_rule=None,
            status=final_status,
            error_message=error_message,
        )
        append_workflow_run_event(
            self.run_id,
            'stage_finished',
            stage_id=self.current_stage_id,
            rule_name=self.current_rule,
            message=f'Stage finished with status {final_status}',
            payload={'status': final_status, 'error_message': error_message},
        )

    def _mark_stage_completed(self, stage_id: str, finished_at: str | None = None) -> None:
        stage = self.stage_lookup.get(stage_id)
        if not stage:
            return
        update_workflow_stage(
            self.run_id,
            stage_id,
            status='completed',
            finished_at=finished_at or _now_str(),
            current_rule=None,
            completed_rules=len(stage.get('rules', [])),
            total_rules=len(stage.get('rules', [])),
        )
        append_workflow_run_event(
            self.run_id,
            'stage_completed',
            stage_id=stage_id,
            message=f"Stage completed: {stage['title']}",
        )


def _collect_workflow_artifacts(workflow_context: dict | None) -> list[dict]:
    workflow_context = workflow_context or {}
    candidate_dirs = [
        workflow_context.get('results_dir'),
        workflow_context.get('reports_dir'),
    ]
    artifacts = []
    seen_paths = set()
    interesting_suffixes = {'.html', '.tsv', '.txt', '.xml', '.yaml', '.yml', '.mzml', '.fasta', '.fa', '.fna', '.faa'}
    for candidate in candidate_dirs:
        if not candidate:
            continue
        base_path = Path(candidate)
        if not base_path.exists():
            continue
        for path in sorted(base_path.rglob('*')):
            if len(artifacts) >= 200:
                break
            if not path.is_file():
                continue
            if path.suffix.lower() not in interesting_suffixes:
                continue
            resolved = str(path.resolve())
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            artifacts.append({
                'label': path.name,
                'path': resolved,
                'kind': path.suffix.lower().lstrip('.') or 'file',
                'size_bytes': path.stat().st_size,
            })
    return artifacts


def _update_manifest_after_run(workflow_context: dict | None, *, status: str, exit_code: int | None = None, error_message: str | None = None, artifacts: list[dict] | None = None) -> None:
    workflow_context = workflow_context or {}
    manifest_path = workflow_context.get('manifest_path')
    if not manifest_path:
        return
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return
    try:
        manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    except Exception:
        manifest = load_workflow_manifest(workflow_context.get('run_id')) or {}
    manifest['status'] = status
    manifest['exit_code'] = exit_code
    manifest['error_message'] = error_message
    manifest['artifacts'] = artifacts or []
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')


def _run_cleanup_commands(cleanup_commands: list[dict], env: dict, log_file) -> None:
    for cleanup in cleanup_commands or []:
        argv = cleanup.get('argv') or []
        if not argv:
            continue
        cwd = cleanup.get('cwd')
        _write_log_line(log_file, f"[SYSTEM] Running cleanup command: {' '.join(argv)}")
        try:
            result = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            output = (result.stdout or '').strip()
            if output:
                for line in output.splitlines():
                    _write_log_line(log_file, line)
            _write_log_line(log_file, f"[SYSTEM] Cleanup exit code: {result.returncode}")
        except Exception as exc:
            _write_log_line(log_file, f"[SYSTEM] Cleanup failed: {exc}")


def run_pipeline_job(
    job_id: str,
    project_id: str,
    tool_name: str,
    command: str,
    log_path: str,
    command_spec: dict | None = None,
) -> dict:
    start_time = time.time()

    existing_job = get_job(job_id)
    if existing_job and existing_job.get('status') == 'canceled':
        return {'status': 'canceled', 'skipped': True}
    if is_cancel_requested(job_id):
        mark_job_finished(job_id, 'canceled', None, 'Canceled before execution', 0)
        return {'status': 'canceled', 'skipped': True}

    mark_job_started(job_id)
    update_job_heartbeat(job_id)

    base_dir = _backend_dir()
    project_dir = os.path.join(base_dir, 'projects', project_id)
    _ensure_directory(project_dir)
    _ensure_directory(os.path.dirname(log_path))

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'

    process: Optional[subprocess.Popen] = None
    workflow_context = (command_spec or {}).get('workflow_context') or {}
    workflow_tracker = WorkflowExecutionTracker(workflow_context)
    _update_manifest_after_run(workflow_context, status='running')
    try:
        with open(log_path, 'a', encoding='utf-8') as log_file:
            _write_log_line(log_file, f"[SYSTEM] Starting command: {command}")

            argv = (command_spec or {}).get('argv') or []
            if not argv:
                raise ValueError('Command specification is missing argv; shell fallback is disabled.')

            cwd = (command_spec or {}).get('cwd', project_dir)
            env.update((command_spec or {}).get('env') or {})

            process = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                cwd=cwd,
                shell=False,
                start_new_session=(os.name != 'nt'),
            )
            attach_process_info(
                job_id,
                pid=process.pid,
                pgid=(process.pid if os.name != 'nt' else None),
                host=socket.gethostname(),
            )
            last_heartbeat = time.monotonic()

            while True:
                if is_cancel_requested(job_id):
                    _write_log_line(log_file, "[SYSTEM] Cancellation requested. Stopping process...")
                    _terminate_process(process, log_file)
                    _run_cleanup_commands((command_spec or {}).get('cleanup_commands') or [], env, log_file)
                    end_time = time.time()
                    workflow_tracker.finalize('canceled', error_message='Canceled by user')
                    artifacts = _collect_workflow_artifacts(workflow_context)
                    if workflow_context.get('run_id'):
                        replace_workflow_artifacts(workflow_context['run_id'], artifacts)
                    _update_manifest_after_run(workflow_context, status='canceled', error_message='Canceled by user', artifacts=artifacts)
                    mark_job_finished(job_id, 'canceled', None, 'Canceled by user', end_time - start_time)
                    return {'status': 'canceled'}

                if process.stdout is None:
                    break

                if select and os.name != 'nt':
                    ready, _, _ = select.select([process.stdout], [], [], 0.5)
                    if not ready:
                        if time.monotonic() - last_heartbeat >= 5:
                            update_job_heartbeat(job_id)
                            last_heartbeat = time.monotonic()
                        if process.poll() is not None:
                            break
                        continue
                    output = process.stdout.readline()
                else:
                    output = process.stdout.readline()

                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.rstrip('\n')
                    _write_log_line(log_file, line)
                    workflow_tracker.handle_line(line)
                if time.monotonic() - last_heartbeat >= 5:
                    update_job_heartbeat(job_id)
                    last_heartbeat = time.monotonic()

            return_code = process.wait()
            end_time = time.time()

            if return_code == 0:
                _write_log_line(log_file, f"[SYSTEM] Task '{tool_name}' completed successfully with exit code {return_code}")
                workflow_tracker.finalize('completed')
                artifacts = _collect_workflow_artifacts(workflow_context)
                if workflow_context.get('run_id'):
                    replace_workflow_artifacts(workflow_context['run_id'], artifacts)
                    append_workflow_run_event(
                        workflow_context['run_id'],
                        'artifacts_collected',
                        message=f'Collected {len(artifacts)} artifacts',
                        payload={'artifact_count': len(artifacts)},
                    )
                _update_manifest_after_run(workflow_context, status='completed', exit_code=return_code, artifacts=artifacts)
                mark_job_finished(job_id, 'completed', return_code, None, end_time - start_time)
                return {'status': 'completed', 'exit_code': return_code}

            _write_log_line(log_file, f"[SYSTEM] Task '{tool_name}' failed with exit code {return_code}")
            workflow_tracker.finalize('failed', error_message=f'Exit code {return_code}')
            artifacts = _collect_workflow_artifacts(workflow_context)
            if workflow_context.get('run_id'):
                replace_workflow_artifacts(workflow_context['run_id'], artifacts)
            _update_manifest_after_run(workflow_context, status='failed', exit_code=return_code, error_message=f'Exit code {return_code}', artifacts=artifacts)
            mark_job_finished(job_id, 'failed', return_code, None, end_time - start_time)
            return {'status': 'failed', 'exit_code': return_code}

    except Exception as exc:
        end_time = time.time()
        error_message = f"Exception occurred: {exc}"
        try:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                _write_log_line(log_file, f"[SYSTEM] {error_message}")
        except Exception:
            pass
        workflow_tracker.finalize('failed', error_message=error_message)
        artifacts = _collect_workflow_artifacts(workflow_context)
        if workflow_context.get('run_id'):
            replace_workflow_artifacts(workflow_context['run_id'], artifacts)
        _update_manifest_after_run(workflow_context, status='failed', error_message=error_message, artifacts=artifacts)
        mark_job_finished(job_id, 'failed', None, error_message, end_time - start_time)
        return {'status': 'failed', 'error': error_message}
    finally:
        if process and process.stdout:
            try:
                process.stdout.close()
            except Exception:
                pass
