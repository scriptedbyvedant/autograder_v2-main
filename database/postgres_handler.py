# File: database/postgres_handler.py

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from datetime import datetime

class PostgresHandler:
    _pool = None

    def __init__(self, conn_params=None):
        if PostgresHandler._pool is None:
            if conn_params is None:
                conn_params = {
                    'host':     'localhost',
                    'port':     5432,
                    'database': 'autograder_db',
                    'user':     'vedant',
                    'password': 'vedant'
                }
            PostgresHandler._pool = psycopg2.pool.SimpleConnectionPool(1, 20, **conn_params)
        
        self.conn = None
        self.initialize_schema()

    def connect(self):
        if self.conn is None or getattr(self.conn, 'closed', True):
            self.conn = PostgresHandler._pool.getconn()

    def close(self):
        if self.conn and not getattr(self.conn, 'closed', True):
            PostgresHandler._pool.putconn(self.conn)
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def initialize_schema(self):
        """Creates tables, adds missing columns, and creates indexes."""
        self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS grading_results (
                    id SERIAL PRIMARY KEY,
                    student_id VARCHAR NOT NULL, professor_id VARCHAR NOT NULL, course VARCHAR, semester VARCHAR,
                    assignment_no VARCHAR NOT NULL, question TEXT NOT NULL, student_answer TEXT, language VARCHAR(50),
                    old_score FLOAT, new_score FLOAT, old_feedback TEXT, new_feedback TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (student_id, assignment_no, question)
                );""")
                cur.execute("""
                CREATE TABLE IF NOT EXISTS grading_corrections (
                    id SERIAL PRIMARY KEY,
                    student_id VARCHAR NOT NULL, professor_id VARCHAR NOT NULL, assignment_no VARCHAR NOT NULL, question TEXT NOT NULL,
                    old_score FLOAT, new_score FLOAT, old_feedback TEXT, new_feedback TEXT, editor_id VARCHAR NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );""")
                cur.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='grading_corrections' AND column_name='language') THEN
                            ALTER TABLE grading_corrections ADD COLUMN language VARCHAR(50);
                        END IF;
                    END $$;
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_gr_prof_assign ON grading_results (professor_id, assignment_no);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_gr_student_id ON grading_results (student_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_gc_editor_assign ON grading_corrections (editor_id, assignment_no);")
            self.conn.commit()
        finally:
            self.close()

    def execute_query(self, query: str, params: tuple = None, fetch: str = None):
        self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch == "one": return cur.fetchone()
                if fetch == "all": return cur.fetchall()
                self.conn.commit()
        finally:
            self.close()
        return None

    def insert_or_update_grading_result(self, *args, **kwargs) -> int:
        self.connect()
        try:
            with self.conn.cursor() as cur:
                sql = '''
                INSERT INTO grading_results (student_id, professor_id, course, semester, assignment_no, question,
                    student_answer, language, old_score, new_score, old_feedback, new_feedback, created_at)
                VALUES (%(student_id)s, %(professor_id)s, %(course)s, %(semester)s, %(assignment_no)s, %(question)s,
                        %(student_answer)s, %(language)s, %(old_score)s, %(new_score)s, %(old_feedback)s, %(new_feedback)s, %(created_at)s)
                ON CONFLICT (student_id, assignment_no, question) DO UPDATE
                    SET new_score = EXCLUDED.new_score, new_feedback = EXCLUDED.new_feedback, student_answer = EXCLUDED.student_answer,
                        language = EXCLUDED.language, course = EXCLUDED.course, semester = EXCLUDED.semester, professor_id = EXCLUDED.professor_id
                RETURNING id;
                '''
                params = dict(zip([
                    "student_id", "professor_id", "course", "semester", "assignment_no", "question", "student_answer",
                    "language", "old_score", "new_score", "old_feedback", "new_feedback"
                ], args))
                params.update(kwargs)
                params['created_at'] = datetime.now()

                cur.execute(sql, params)
                rid = cur.fetchone()[0]
            self.conn.commit()
            return rid
        except Exception:
            if self.conn: self.conn.rollback()
            raise
        finally:
            self.close()

    def insert_grading_result(self, *args, **kwargs) -> int:
        return self.insert_or_update_grading_result(*args, **kwargs)

    def _insert_grading_correction_with_cursor(self, cur, student_id: str, professor_id: str, assignment_no: str, question: str,
                                  old_score: float, new_score: float, old_feedback: str, new_feedback: str,
                                  editor_id: str, language: str) -> None:
        cur.execute(
            '''
            INSERT INTO grading_corrections (student_id, professor_id, assignment_no, question, old_score, new_score,
                old_feedback, new_feedback, editor_id, language, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            ''',
            (student_id, professor_id, assignment_no, question, old_score, new_score,
             old_feedback, new_feedback, editor_id, language, datetime.now())
        )

    def insert_grading_correction(self, *args, **kwargs) -> None:
        self.connect()
        try:
            with self.conn.cursor() as cur:
                self._insert_grading_correction_with_cursor(cur, *args, **kwargs)
            self.conn.commit()
        except Exception:
            if self.conn: self.conn.rollback()
            raise
        finally:
            self.close()

    def update_grading_result_with_correction(self, grading_result_id: int, new_score: float,
                                              new_feedback: str, editor_id: str) -> None:
        self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, student_id, professor_id, assignment_no, question, language, new_score, new_feedback FROM grading_results WHERE id = %s FOR UPDATE;",
                    (grading_result_id,)
                )
                record = cur.fetchone()
                if not record:
                    raise ValueError(f"Grading result id {grading_result_id} not found")

                self._insert_grading_correction_with_cursor(
                    cur,
                    student_id=record['student_id'], professor_id=record['professor_id'],
                    assignment_no=record['assignment_no'], question=record['question'],
                    old_score=record['new_score'], new_score=new_score,
                    old_feedback=record['new_feedback'], new_feedback=new_feedback,
                    editor_id=editor_id, language=record.get('language', 'English') # Safely access language
                )

                cur.execute(
                    "UPDATE grading_results SET new_score = %s, new_feedback = %s, created_at = %s WHERE id = %s;",
                    (new_score, new_feedback, datetime.now(), grading_result_id)
                )
            self.conn.commit()
        except Exception:
            if self.conn: self.conn.rollback()
            raise
        finally:
            self.close()

    def fetch_results(self, filters: dict = None) -> list:
        self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT id, student_id, professor_id, course, semester, assignment_no, question, student_answer, language, old_score, new_score, old_feedback, new_feedback, created_at FROM grading_results WHERE 1=1"
                params = []
                if filters:
                    pid = filters.get('professor_id')
                    if pid and pid != 'All':
                        query += " AND professor_id = %s"
                        params.append(pid)
                    for fld in ("course","semester","assignment_no","student_id","language"):
                        val = filters.get(fld)
                        if val and val != "All":
                            query += f" AND {fld} = %s"
                            params.append(val)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            for r in rows:
                try: r["score_numeric"] = float(r.get("new_score") or 0)
                except: r["score_numeric"] = 0.0
            return rows
        finally:
            self.close()

    def fetch_my_results(self, professor_email: str, filters: dict = None) -> list:
        if filters is None: filters = {}
        filters['professor_id'] = professor_email
        return self.fetch_results(filters)

    def share_result(self, owner_email: str, target_email: str, result_id: int):
        self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM result_shares WHERE owner_professor_email = %s AND shared_with_email = %s AND grading_result_id = %s;",
                    (owner_email, target_email, result_id)
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO result_shares (owner_professor_email, shared_with_email, grading_result_id, created_at) VALUES (%s, %s, %s, %s);",
                        (owner_email, target_email, result_id, datetime.now())
                    )
            self.conn.commit()
        finally:
            self.close()

    def revoke_share(self, owner_email: str, target_email: str, result_id: int):
        self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM result_shares WHERE owner_professor_email = %s AND shared_with_email = %s AND grading_result_id = %s;",
                    (owner_email, target_email, result_id)
                )
            self.conn.commit()
        finally:
            self.close()

    def fetch_shared_with_me(self, my_email: str) -> list:
        self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    '''
                    SELECT gr.*, rs.owner_professor_email AS shared_by
                      FROM grading_results gr
                      JOIN result_shares rs ON gr.id = rs.grading_result_id
                     WHERE rs.shared_with_email = %s;
                    ''',
                    (my_email,)
                )
                rows = cur.fetchall()

            for r in rows:
                try:
                    r["score_numeric"] = float(r.get("new_score") or 0)
                except:
                    r["score_numeric"] = 0.0
            return rows
        finally:
            self.close()

    def fetch_my_shares(self, owner_email: str) -> list:
        self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    '''
                    SELECT rs.grading_result_id AS result_id, rs.shared_with_email  AS shared_with, rs.created_at
                      FROM result_shares rs
                     WHERE rs.owner_professor_email = %s
                     ORDER BY rs.created_at DESC;
                    ''',
                    (owner_email,)
                )
                shares = cur.fetchall()
            return shares
        finally:
            self.close()
