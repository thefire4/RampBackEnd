-- Existing databases only; fresh installations use SQL_Setup.sql.
USE RampCoreOs;
ALTER TABLE files
    ADD COLUMN source_sheet VARCHAR(255) NULL,
    ADD COLUMN source_file_id INT NULL,
    ADD CONSTRAINT fk_files_source_file FOREIGN KEY (source_file_id)
        REFERENCES files(id) ON DELETE SET NULL;
