import unittest
from api.workspace import process

class WorkspaceTest(unittest.TestCase):
    def setUp(self):self.snapshot=None
    def request(self,action,data=None):
        r=process({'project':'pulse','action':action,'data':data or {},'snapshot':self.snapshot})
        self.snapshot=r['snapshot']
        return r['result']
    def test_primary_flow(self):
        state=self.request('state')
        monitor=next(m for m in state['monitors'] if m['url']=='/sample/unavailable')
        check=self.request('check',{'id':monitor['id']})
        self.assertEqual(check['status'],503)
        self.assertFalse(check['ok'])
        self.assertTrue(self.request('state')['incidents'])
    def test_reject_other_project(self):
        with self.assertRaises(ValueError):
            process({'project':'affiliate','action':'state','data':{}})
