-- Existing databases only. Fresh installations use SQL_Setup.sql.
-- Optional columns preserve current BOM data and completeness calculations.
USE RampCoreOs;
ALTER TABLE project_materials
    ADD COLUMN supplied_by VARCHAR(255) NULL,
    ADD COLUMN required_arrival DATE NULL,
    ADD COLUMN sourcing_status ENUM('awaiting', 'delayed', 'in stock') NULL,
    ADD COLUMN approvals_needed TEXT NULL;
