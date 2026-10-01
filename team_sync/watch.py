"""Watch repository refs and publish metadata-only updates; no AI calls."""
import argparse
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .store import TeamStore, PROJECTS


def refs(project):
    remote = f'https://github.com/gabrielcinematographer/{project}.git'
    result = subprocess.run(['git','ls-remote','--heads',remote],capture_output=True,text=True,timeout=45)
    if result.returncode:
        raise RuntimeError('GitHub read failed for '+project)
    return dict(line.split('\t',1)[::-1] for line in result.stdout.splitlines())


def changed(before, after):
    return sum(before.get(k) != after.get(k) for k in before.keys() | after.keys())


def scan(root, store, fetch=refs):
    root = Path(root)
    root.mkdir(parents=True,exist_ok=True)
    state_path = root/'watch-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    for project in PROJECTS:
        try:
            current = fetch(project)
            previous = state.get(project)
            if previous is not None and project != 'agents' and changed(previous,current):
                # No branch names, commit text, source files or private chat content leave the worker.
                fingerprint = json.dumps(current,sort_keys=True)
                event_id = str(uuid.uuid5(uuid.NAMESPACE_URL,project+fingerprint))
                store.publish(project,'codex',
                    'New GitHub changes detected; project workers should refresh before continuing.',
                    'GitHub branch references changed; no source content was copied to this public desk.',
                    'Read the project latest handoff and changes in its own repository.',
                    event_id=event_id)
                # Advance state only after successful publication, so failures can retry.
            state[project] = current
            print(project+': checked',flush=True)
        except (RuntimeError,subprocess.TimeoutExpired) as error:
            print(project+': check failed ('+type(error).__name__+')',flush=True)
    tmp=state_path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state,sort_keys=True))
    tmp.replace(state_path)
    return state


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--interval',type=int,default=30)
    args=parser.parse_args()
    if args.interval < 15:parser.error('Minimum interval is 15 seconds')
    root=Path(os.environ.get('TEAM_SYNC_DIR','/workspace/agents/runtime/team-sync'))
    store=TeamStore(root)
    # One watcher per cache. The store uses its own independent transaction lock.
    import fcntl
    root.mkdir(parents=True,exist_ok=True)
    with (root/'watch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            scan(root,store)
            if args.once:break
            time.sleep(args.interval)

if __name__=='__main__':main()
