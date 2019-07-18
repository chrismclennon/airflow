# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
import datetime
import unittest

import pendulum
from sqlalchemy.exc import StatementError

from airflow import settings
from airflow.models import DAG, DagRun
from airflow.settings import Session
from airflow.utils.state import State
from airflow.utils.timezone import utcnow


class TestSqlAlchemyUtils(unittest.TestCase):
    def setUp(self):
        session = Session()

        # make sure NOT to run in UTC. Only postgres supports storing
        # timezone information in the datetime field
        if session.bind.dialect.name == "postgresql":
            session.execute("SET timezone='Europe/Amsterdam'")

        self.session = session

    def test_utc_transformations(self):
        """
        Test whether what we are storing is what we are retrieving
        for datetimes
        """
        dag_id = 'test_utc_transformations'
        start_date = utcnow()
        iso_date = start_date.isoformat()
        execution_date = start_date + datetime.timedelta(hours=1, days=1)

        dag = DAG(
            dag_id=dag_id,
            start_date=start_date,
        )
        dag.clear()

        run = dag.create_dagrun(
            run_id=iso_date,
            state=State.NONE,
            execution_date=execution_date,
            start_date=start_date,
            session=self.session,
        )

        self.assertEqual(execution_date, run.execution_date)
        self.assertEqual(start_date, run.start_date)

        self.assertEqual(execution_date.utcoffset().total_seconds(), 0.0)
        self.assertEqual(start_date.utcoffset().total_seconds(), 0.0)

        self.assertEqual(iso_date, run.run_id)
        self.assertEqual(run.start_date.isoformat(), run.run_id)

        dag.clear()

    def test_process_bind_param_naive(self):
        """
        Check if naive datetimes are prevented from saving to the db
        """
        dag_id = 'test_process_bind_param_naive'

        # naive
        start_date = datetime.datetime.now()
        dag = DAG(dag_id=dag_id, start_date=start_date)
        dag.clear()

        with self.assertRaises((ValueError, StatementError)):
            dag.create_dagrun(
                run_id=start_date.isoformat,
                state=State.NONE,
                execution_date=start_date,
                start_date=start_date,
                session=self.session
            )

    def test_pendulum_instance(self):
        """
        Check that pendulum DateTimes are returned from database
        """
        dag_id = 'test_pendulum_instance'
        start_date = utcnow()
        iso_date = start_date.isoformat()
        execution_date = start_date + datetime.timedelta(hours=1, days=1)

        dag = DAG(
            dag_id=dag_id,
            start_date=start_date,
        )
        dag.clear()

        run = dag.create_dagrun(
            run_id=iso_date,
            state=State.NONE,
            execution_date=execution_date,
            start_date=start_date,
            session=self.session,
        )

        run = DagRun.get_run(
            self.session,
            dag_id,
            execution_date=execution_date,
        )

        self.assertIsInstance(run.execution_date, pendulum.now().__class__)

        dag.clear()

    def tearDown(self):
        self.session.close()
        settings.engine.dispose()
