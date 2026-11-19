USE RampCoreOs;

CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bom_line_id INT NOT NULL,
    project_id INT NOT NULL,
    missing_fields JSON NOT NULL,
    owner_id INT NULL,
    status ENUM('open', 'in progress', 'done') NOT NULL DEFAULT 'open',
    due_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE (bom_line_id),
    FOREIGN KEY (bom_line_id)
        REFERENCES project_materials(id)
        ON DELETE CASCADE,
    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE,
    FOREIGN KEY (owner_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);
