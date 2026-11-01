ALTER TABLE project_materials
    MODIFY COLUMN quantity DOUBLE NULL;

CREATE TABLE IF NOT EXISTS project_change_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE,
    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);
