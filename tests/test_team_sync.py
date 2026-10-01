import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from team_sync.store import TeamStore

def git(path, *args):
    return subprocess.run(['git','-C',str(path),*args],check=True,capture_output=True,text=True).stdout

class SharedGitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote = root/'remote.git'
        subprocess.run(['git','init','--bare',str(self.remote)],check=True,capture_output=True)
        seed = root/'seed'
        seed.mkdir()
        git(seed,'init','-b','main')
        git(seed,'config','user.name','Test')
        git(seed,'config','user.email','test@example.invalid')
        (seed/'README.md').write_text('Test team desk\n')
        git(seed,'add','README.md')
        git(seed,'commit','-m','Initial')
        git(seed,'remote','add','origin',str(self.remote))
        git(seed,'push','origin','main')
        self.a = TeamStore(root/'a',str(self.remote))
        self.b = TeamStore(root/'b',str(self.remote))

    def post(self, store, provider='claude', **extra):
        return store.publish('design',provider,'Checked layout','commit abc','Review result',**extra)

    def test_visible_to_another_worker_after_restart(self):
        result = self.post(self.a)
        restarted = TeamStore(self.b.root,str(self.remote))
        updates = restarted.read('design')['updates']
        self.assertEqual(updates[0]['event_id'],result['event_id'])
        self.assertEqual(updates[0]['provider'],'claude')

    def test_new_updates_preserve_other_teams(self):
        self.b.read('design')
        self.post(self.a)
        self.post(self.b,'grok')
        self.assertEqual(len(self.a.read('design')['updates']),2)

    def test_duplicate_is_idempotent_and_conflict_rejected(self):
        result = self.post(self.a)
        again = self.post(self.b,event_id=result['event_id'])
        self.assertEqual(again['status'],'already_published')
        with self.assertRaises(ValueError):
            self.post(self.b,'jev',event_id=result['event_id'])

    def test_bad_scope_or_payload_is_rejected_before_git(self):
        with self.assertRaises(ValueError):
            self.a.read('../trading')
        with self.assertRaises(ValueError):
            self.a.publish('trading','someone','x','proof','next')
        with self.assertRaises(ValueError):
            self.a.publish('trading','codex','x'*4001,'proof','next')

    def test_rejected_push_retries_without_losing_remote_updates(self):
        original = self.a.git
        raced = False
        def intercepted(*args):
            nonlocal raced
            if args[0] == 'push' and not raced:
                raced = True
                self.post(self.b,'jev')
            return original(*args)
        self.a.git = intercepted
        self.post(self.a)
        self.assertEqual(len(self.b.read('design')['updates']),2)

if __name__=='__main__':unittest.main()
