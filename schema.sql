-- File: schema.sql

-- Drop existing tables if you need a clean slate
DROP TABLE IF EXISTS grading_corrections;
DROP TABLE IF EXISTS grading_results;

-- grading_results with multilingual support
CREATE TABLE grading_results (
    id              SERIAL PRIMARY KEY,
    student_id      VARCHAR   NOT NULL,
    professor_id    VARCHAR   NOT NULL,
    course          VARCHAR   NOT NULL,
    semester        VARCHAR   NOT NULL,
    assignment_no   VARCHAR   NOT NULL,
    question        TEXT      NOT NULL,
    student_answer  TEXT,
    score           NUMERIC,
    final_feedback  TEXT,
    language        VARCHAR(32) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, assignment_no, question)
);

-- Index on language for faster filtering
CREATE INDEX IF NOT EXISTS idx_grading_results_language
  ON grading_results(language);

-- grading_corrections with language tracking
CREATE TABLE grading_corrections (
    id               SERIAL PRIMARY KEY,
    student_id       VARCHAR   NOT NULL,
    professor_id     VARCHAR   NOT NULL,
    assignment_no    VARCHAR   NOT NULL,
    question         TEXT      NOT NULL,
    old_score        NUMERIC,
    new_score        NUMERIC,
    old_feedback     TEXT,
    new_feedback     TEXT,
    editor_id        VARCHAR   NOT NULL,
    language         VARCHAR(32) NOT NULL DEFAULT 'English',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index on corrections language for faster filtering
CREATE INDEX IF NOT EXISTS idx_grading_corrections_language
  ON grading_corrections(language);
