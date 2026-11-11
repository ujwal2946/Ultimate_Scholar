-- Run once on existing databases created with the previous schema.
ALTER TABLE students
  DROP INDEX parent_email,
  DROP INDEX parent_phone;
