import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import alerts
import service as s


class AlertTests(unittest.TestCase):
    now = 1789000000000

    def points(self, values):
        return [(self.now-(len(values)-i-1)*10000, value) for i, value in enumerate(values)]

    def test_sustained_duration_and_threshold(self):
        for values, expected in (([90]*4, 'active'), ([90]*3, 'pending'),
                                 ([90, 80, 90, 90], 'pending'), ([90, 80], 'normal')):
            with self.subTest(values=values):
                self.assertEqual(alerts.sustained(self.points(values), 80, 30, self.now)['state'], expected)

    def test_gaps_and_stale_samples_do_not_confirm_an_alarm(self):
        points=self.points([90]*5)
        del points[2]
        self.assertEqual(alerts.sustained(points,80,30,self.now)['state'],'pending')
        self.assertEqual(alerts.sustained(points,80,30,self.now+60001)['state'],'unknown')
        self.assertEqual(alerts.sustained([],80,30,self.now)['state'],'unknown')

    def test_host_memory_percentage_and_cpu_independence(self):
        with tempfile.TemporaryDirectory() as directory:
            db=s.Database(Path(directory)/'test.sqlite')
            db.inventory('host',[],self.now)
            config={'servers':[{'id':'host','name':'Host','enabled':True}]}
            samples=[{'time':ts,'value':value,'total':100} for ts,value in self.points([90]*4)]
            with patch.object(s.time,'time',return_value=self.now/1000):
                db.ingest('host','','memory',samples,self.now-40000,self.now)
            target=alerts.evaluate(config,db,{},self.now)['targets'][0]
            self.assertEqual(target['state'],'active')
            self.assertEqual(target['metrics']['memory']['value'],90)
            self.assertEqual(target['metrics']['cpu']['state'],'unknown')

    def test_replicas_must_have_complete_samples_and_memory_uses_mib(self):
        with tempfile.TemporaryDirectory() as directory:
            db=s.Database(Path(directory)/'test.sqlite')
            resources=[{'source':replica,'id':'app','name':'App','kind':'application','project':'Example','state':'running'} for replica in ('a','b')]
            db.inventory('host',resources,self.now)
            config={'servers':[{'id':'host','name':'Host','enabled':True}]}
            query={'server':['host'],'entity':['app'],'memory':['100']}
            samples=[{'time':ts,'value':value*1048576} for ts,value in self.points([60]*5)]
            db.ingest('host','a','memory',samples,self.now-40000,self.now)
            db.ingest('host','b','memory',samples[-2:],self.now-40000,self.now)
            target=alerts.evaluate(config,db,query,self.now)['targets'][0]
            self.assertNotEqual(target['state'],'active')
            db.ingest('host','b','memory',samples,self.now-40000,self.now)
            target=alerts.evaluate(config,db,query,self.now)['targets'][0]
            self.assertEqual(target['state'],'active')
            self.assertEqual(target['metrics']['memory']['value'],120*1048576)
            with db.connect() as conn:
                conn.execute('INSERT INTO status VALUES(?,?,?)',('host',self.now,'Offline'))
            self.assertEqual(alerts.evaluate(config,db,query,self.now)['targets'][0]['state'],'unknown')

    def test_invalid_rule_is_rejected(self):
        for query in ({'cpu':['nan']},{'memory':['101']},{'seconds':['0']},{'entity':['app']}):
            with self.subTest(query=query), self.assertRaises(s.Problem):
                alerts.evaluate({'servers':[]},None,query,self.now)

    def test_projects_group_replicas_and_exclude_missing_and_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            db=s.Database(Path(directory)/'test.sqlite')
            resources=[{'source':r,'id':'app','name':'App','kind':'application','project':'Example','state':'running'} for r in ('a','b')]
            db.inventory('host',resources,self.now)
            db.inventory('disabled',resources,self.now)
            config={'servers':[{'id':'host','name':'Host','enabled':True},{'id':'disabled','name':'Disabled','enabled':False}]}
            dashboard=s.Dashboard(config,db)
            groups=dashboard.route('/api/projects',{})['projects']
            self.assertEqual(len(groups),1)
            self.assertEqual(len(groups[0]['resources']),1)
            db.inventory('host',[],self.now+10000)
            self.assertEqual(dashboard.route('/api/projects',{})['projects'],[])
