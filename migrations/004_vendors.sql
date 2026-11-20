USE RampCoreOs;

CREATE TABLE IF NOT EXISTS vendors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    notes TEXT
);

ALTER TABLE project_materials
    ADD COLUMN vendor_id INT NULL,
    ADD CONSTRAINT fk_project_materials_vendor
        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        ON DELETE SET NULL;
