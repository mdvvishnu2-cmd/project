-- Online Voting System Database Schema
-- Run this file to set up the database

CREATE DATABASE IF NOT EXISTS voting_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE voting_system;

-- Voters table
CREATE TABLE IF NOT EXISTS voters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    register_number VARCHAR(50) UNIQUE NOT NULL,
    department VARCHAR(100) NOT NULL,
    voter_id VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    address TEXT,
    is_verified BOOLEAN DEFAULT TRUE,
    has_voted BOOLEAN DEFAULT FALSE,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- Candidates table
CREATE TABLE IF NOT EXISTS candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    party VARCHAR(100),
    position VARCHAR(100) NOT NULL,
    bio TEXT,
    photo VARCHAR(255),
    manifesto TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Elections table
CREATE TABLE IF NOT EXISTS elections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Votes table
CREATE TABLE IF NOT EXISTS votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    voter_id INT NOT NULL,
    candidate_id INT NOT NULL,
    election_id INT NOT NULL,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    UNIQUE KEY unique_vote (voter_id, election_id)
);

-- Admins table
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_super_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    performed_by VARCHAR(100),
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin (password: Admin@123)
INSERT INTO admins (username, email, password_hash, is_super_admin) VALUES
('admin', 'admin@voting.com', 'scrypt:32768:8:1$vXt4fBUtcYrn1v6j$cd148da3df267e7c4efc71bb482ee17f300c14b7e800318610ccfc3aae6c825a0a1fc41cd0caba5d95d852db16ba58d5bd2a222ab59dmin.e55ac36bdd7bf6ec85', TRUE)
ON DUPLICATE KEY UPDATE username = username;

-- Insert sample election
INSERT INTO elections (title, description, start_date, end_date, is_active) VALUES
('College Union Election 2025', 'Annual election to select the college union representatives.', '2025-01-01 00:00:00', '2025-12-31 23:59:59', TRUE)
ON DUPLICATE KEY UPDATE title = title;

-- Insert sample candidates
INSERT INTO candidates (name, party, position, bio, is_active) VALUES
('Alexandra Chen', 'BSc Computer Science', 'President', 'Current student representative with strong academic record, focused on campus facility improvements.', TRUE),
('Marcus Williams', 'BSc Information Technology', 'President', 'Tech enthusiast and debate club leader, advocating for better lab equipment and placement drives.', TRUE),
('Sarah Johnson', 'BBA', 'General Secretary', 'Event management head with plans for more inter-collegiate fests and sports events.', TRUE),
('Robert Kim', 'BCom', 'Vice President', 'Finance club president committed to transparent student union funding and new scholarship schemes.', TRUE)
ON DUPLICATE KEY UPDATE name = name;
