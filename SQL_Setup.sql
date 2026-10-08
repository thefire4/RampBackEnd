
CREATE DATABASE IF NOT EXISTS RampCoreOs;

USE RampCoreOs;

-- Users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status ENUM('blocked', 'in progress', 'finished')
        NOT NULL DEFAULT 'in progress',
    style_no VARCHAR(100),
    po_no VARCHAR(100),
    project_date DATE,
    customer VARCHAR(255),
    size_range VARCHAR(50),
    season VARCHAR(50),
    fabric_yarn VARCHAR(100),
    designer VARCHAR(100),
    weight VARCHAR(100),
    description VARCHAR(1000)
);

-- Users assigned to projects (many-to-many)
CREATE TABLE IF NOT EXISTS project_users (
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (project_id, user_id),

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- Project colorways
CREATE TABLE IF NOT EXISTS project_colors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    project_id INT NOT NULL,

    UNIQUE (project_id, name),

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

-- Materials associated with each colorway
CREATE TABLE IF NOT EXISTS project_materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    colorway_id INT NOT NULL,
    name VARCHAR(50),
    material VARCHAR(100),
    supplier VARCHAR(100),
    supplier_contact VARCHAR(255),
    quantity DECIMAL(10, 2),
    location VARCHAR(1000),
    article_no VARCHAR(100),
    material_size VARCHAR(50),
    uom VARCHAR(10),
    notes TEXT,

    FOREIGN KEY (colorway_id)
        REFERENCES project_colors(id)
        ON DELETE CASCADE
);

-- Project measurement points
CREATE TABLE IF NOT EXISTS points_measured (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    code VARCHAR(10),
    name VARCHAR(100),
    tol VARCHAR(10),
    sizes VARCHAR(10),
    measure VARCHAR(10),
    grade VARCHAR(10),
    notes TEXT,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

-- Files attached to projects
CREATE TABLE IF NOT EXISTS files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- Project comments, optionally linked to a file
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    file_id INT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (file_id)
        REFERENCES files(id)
        ON DELETE SET NULL
);
