"""Small Git-backed handoff store. Never calls an AI provider."""
import fcntl
import json
import subprocess
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PROJECTS = ('agents', 'trading', 'design', 'cinematography', 'pitchdeck')
PROVIDERS = ('codex', 'claude', 'grok', 'jev', 'nvidia', 'google', 'human')
REMOTE = 'https://github.com/gabrielcinematographer/agents.git'

class TeamStore:
    def __init__(self, root, remote=REMOTE):
        self.root = Path(root)
        self.repo = self.root / 'checkout'
        self.remote = remote

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.repo), *args],
                                capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError('Shared Git operation failed; check repository access and network.')
        return result.stdout

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / 'lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not (self.repo / '.git').exists():
                result = subprocess.run(['git', 'clone', '--single-branch', '--branch', 'main',
                                         self.remote, str(self.repo)], capture_output=True, timeout=60)
                if result.returncode:
                    raise RuntimeError('Cannot open shared repository; check GitHub access.')
                self.git('config', 'user.name', 'Cloud team')
                self.git('config', 'user.email', 'cloud-team@users.noreply.github.com')
            yield

    def refresh(self):
        # This checkout is exclusively a disposable tool cache, never a user worktree.
        self.git('fetch', 'origin', 'main')
        self.git('reset', '--hard', 'origin/main')

    def read(self, project):
        if project not in PROJECTS:
            raise ValueError('Unknown project')
        with self.locked():
            self.refresh()
            folder = self.repo / 'team' / 'updates' / project
            updates = [json.loads(p.read_text()) for p in folder.glob('*.json')] if folder.exists() else []
            return {'project': project, 'updates': sorted(updates, key=lambda x:x['timestamp'])[-30:],
                    'revision': self.git('rev-parse', 'HEAD').strip(), 'inference_calls': 0}

    def publish(self, project, provider, completed, evidence, next_step, blockers='', event_id=None):
        if project not in PROJECTS or provider not in PROVIDERS:
            raise ValueError('Unknown project or provider')
        values = (completed, evidence, next_step, blockers)
        if any(not isinstance(v, str) or len(v) > 4000 for v in values):
            raise ValueError('Update fields must be text, at most 4000 characters each')
        if not completed.strip() or not evidence.strip():
            raise ValueError('Include completed work and evidence')
        event_id = str(uuid.UUID(event_id)) if event_id else str(uuid.uuid4())
        record = dict(project=project, provider=provider, completed=completed, evidence=evidence,
                      next_step=next_step, blockers=blockers, event_id=event_id,
                      timestamp=datetime.now(timezone.utc).isoformat())
        relative = Path('team') / 'updates' / project / (event_id + '.json')
        with self.locked():
            for attempt in range(3):
                self.refresh()
                target = self.repo / relative
                if target.exists():
                    old = json.loads(target.read_text())
                    if any(old[k] != record[k] for k in record if k != 'timestamp'):
                        raise ValueError('Event ID already belongs to a different update')
                    return {'event_id': event_id, 'status':'already_published', 'inference_calls':0}
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(record, indent=2) + '\n')
                self.git('add', str(relative))
                self.git('commit', '-m', f'Team update: {project} / {provider}')
                try:
                    self.git('push', 'origin', 'HEAD:main')
                    return {'event_id':event_id, 'status':'published',
                            'revision':self.git('rev-parse', 'HEAD').strip(), 'inference_calls':0}
                except RuntimeError:
                    if attempt == 2:
                        raise
