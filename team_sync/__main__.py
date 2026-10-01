import argparse
import json
import os
from .store import TeamStore, PROJECTS, PROVIDERS
parser = argparse.ArgumentParser(description='Shared GitHub updates; no AI calls')
commands = parser.add_subparsers(dest='command', required=True)
read = commands.add_parser('read')
read.add_argument('project', choices=PROJECTS)
post = commands.add_parser('post')
post.add_argument('project', choices=PROJECTS)
post.add_argument('--provider', required=True, choices=PROVIDERS)
post.add_argument('--completed', required=True)
post.add_argument('--evidence', required=True)
post.add_argument('--next-step', required=True)
post.add_argument('--blockers', default='')
args = vars(parser.parse_args())
command = args.pop('command')
store = TeamStore(os.environ.get('TEAM_SYNC_DIR', '/workspace/agents/runtime/team-sync'))
result = store.read(**args) if command == 'read' else store.publish(**args)
print(json.dumps(result, indent=2))
