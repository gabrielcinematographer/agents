import tempfile
import unittest
from unittest.mock import Mock
from team_sync.watch import scan

class WatchTests(unittest.TestCase):
    def test_baseline_then_change_and_no_repeat(self):
        with tempfile.TemporaryDirectory() as root:
            store=Mock()
            values={'main':'aaa'}
            fetch=lambda project:dict(values)
            scan(root,store,fetch)
            store.publish.assert_not_called()
            values['main']='bbb'
            scan(root,store,fetch)
            self.assertEqual(store.publish.call_count,4)
            scan(root,store,fetch)
            self.assertEqual(store.publish.call_count,4)
            self.assertNotIn('bbb',str(store.publish.call_args))

    def test_failed_publish_retries_next_scan(self):
        with tempfile.TemporaryDirectory() as root:
            store=Mock()
            values={'main':'aaa'}
            fetch=lambda project:dict(values)
            scan(root,store,fetch)
            values['main']='bbb'
            store.publish.side_effect=RuntimeError('unavailable')
            scan(root,store,fetch)
            store.publish.side_effect=None
            scan(root,store,fetch)
            self.assertEqual(store.publish.call_count,8)

if __name__=='__main__':unittest.main()
