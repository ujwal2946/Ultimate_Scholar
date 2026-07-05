-- Grades table patch

CREATE TABLE IF NOT EXISTS grades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject VARCHAR(255) NOT NULL,
  marks INT NOT NULL,
  grade VARCHAR(10) NOT NULL,
  semester VARCHAR(50) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_grades_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
  KEY idx_grades_student_semester (student_id, semester),
  KEY idx_grades_student_subject_semester (student_id, subject, semester)
);

