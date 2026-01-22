-- =============================================================================
-- LOCAS - Library for College Administration System
-- Database Schema for MySQL 8+
-- =============================================================================

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS fines;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS book_copies;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

-- =============================================================================
-- 1. ROLES TABLE
-- Stores system roles for role-based access control (RBAC)
-- =============================================================================
CREATE TABLE roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_role_name UNIQUE (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 2. USERS TABLE
-- Stores all system users (admin, librarian, student)
-- =============================================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    
    CONSTRAINT uq_username UNIQUE (username),
    CONSTRAINT uq_email UNIQUE (email),
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) 
        REFERENCES roles(role_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    
    INDEX idx_users_role (role_id),
    INDEX idx_users_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 3. BOOKS TABLE
-- Master catalog of books (logical book entity)
-- =============================================================================
CREATE TABLE books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    publisher VARCHAR(255),
    publication_year YEAR,
    category VARCHAR(100),
    description TEXT,
    total_copies INT DEFAULT 0,
    available_copies INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_isbn UNIQUE (isbn),
    CONSTRAINT chk_copies CHECK (available_copies >= 0 AND available_copies <= total_copies),
    
    INDEX idx_books_title (title),
    INDEX idx_books_author (author),
    INDEX idx_books_category (category),
    FULLTEXT INDEX ft_books_search (title, author, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 4. BOOK_COPIES TABLE
-- Physical copies of books (each has unique barcode)
-- =============================================================================
CREATE TABLE book_copies (
    copy_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    barcode VARCHAR(50) NOT NULL,
    status ENUM('available', 'issued', 'lost', 'damaged', 'reserved') DEFAULT 'available',
    location VARCHAR(100),
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_barcode UNIQUE (barcode),
    CONSTRAINT fk_copies_book FOREIGN KEY (book_id) 
        REFERENCES books(book_id) ON DELETE CASCADE ON UPDATE CASCADE,
    
    INDEX idx_copies_book (book_id),
    INDEX idx_copies_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 5. TRANSACTIONS TABLE
-- Records all book issue/return operations
-- =============================================================================
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    copy_id INT NOT NULL,
    user_id INT NOT NULL,
    issued_by INT NOT NULL,
    issue_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    due_date DATE NOT NULL,
    return_date DATETIME NULL,
    returned_by INT NULL,
    status ENUM('active', 'returned', 'overdue', 'lost') DEFAULT 'active',
    remarks TEXT,
    
    CONSTRAINT fk_trans_copy FOREIGN KEY (copy_id) 
        REFERENCES book_copies(copy_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_trans_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_trans_issued_by FOREIGN KEY (issued_by) 
        REFERENCES users(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_trans_returned_by FOREIGN KEY (returned_by) 
        REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
    
    INDEX idx_trans_copy (copy_id),
    INDEX idx_trans_user (user_id),
    INDEX idx_trans_status (status),
    INDEX idx_trans_due_date (due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 6. FINES TABLE
-- Tracks fines for overdue books
-- =============================================================================
CREATE TABLE fines (
    fine_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    user_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    status ENUM('pending', 'paid', 'waived') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME NULL,
    
    CONSTRAINT uq_fine_transaction UNIQUE (transaction_id),
    CONSTRAINT fk_fines_trans FOREIGN KEY (transaction_id) 
        REFERENCES transactions(transaction_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_fines_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_fine_amount CHECK (amount >= 0),
    
    INDEX idx_fines_user (user_id),
    INDEX idx_fines_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 7. AUDIT_LOGS TABLE
-- Records all admin and librarian actions for accountability
-- =============================================================================
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT,
    old_value JSON,
    new_value JSON,
    ip_address VARCHAR(45),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_entity (entity_type),
    INDEX idx_audit_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Trigger: Update book copy counts when a new copy is added
DELIMITER //
CREATE TRIGGER trg_copy_insert_update_counts
AFTER INSERT ON book_copies
FOR EACH ROW
BEGIN
    UPDATE books 
    SET total_copies = total_copies + 1,
        available_copies = available_copies + 1
    WHERE book_id = NEW.book_id;
END//
DELIMITER ;

-- Trigger: Update book copy counts when a copy is deleted
DELIMITER //
CREATE TRIGGER trg_copy_delete_update_counts
AFTER DELETE ON book_copies
FOR EACH ROW
BEGIN
    UPDATE books 
    SET total_copies = total_copies - 1,
        available_copies = CASE 
            WHEN OLD.status = 'available' THEN available_copies - 1 
            ELSE available_copies 
        END
    WHERE book_id = OLD.book_id;
END//
DELIMITER ;

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Insert default roles
INSERT INTO roles (role_name, description) VALUES
    ('admin', 'System administrator with full access'),
    ('librarian', 'Library staff managing books and transactions'),
    ('student', 'College student with borrowing privileges');

-- Insert default admin user (password: Admin@123)
-- bcrypt hash for 'Admin@123' with 12 rounds
INSERT INTO users (username, password_hash, email, full_name, role_id, is_active) VALUES
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4oaSc.KkNrT.S.E2', 
     'admin@locas.local', 'System Administrator', 1, TRUE);

-- =============================================================================
-- VIEWS (Optional convenience views)
-- =============================================================================

-- View: Active transactions with book and user details
CREATE OR REPLACE VIEW vw_active_transactions AS
SELECT 
    t.transaction_id,
    t.issue_date,
    t.due_date,
    t.status,
    bc.barcode,
    b.title,
    b.author,
    u.username AS borrower_username,
    u.full_name AS borrower_name,
    lib.username AS issued_by_username,
    DATEDIFF(CURDATE(), t.due_date) AS days_overdue
FROM transactions t
JOIN book_copies bc ON t.copy_id = bc.copy_id
JOIN books b ON bc.book_id = b.book_id
JOIN users u ON t.user_id = u.user_id
JOIN users lib ON t.issued_by = lib.user_id
WHERE t.status IN ('active', 'overdue');

-- View: Book availability summary
CREATE OR REPLACE VIEW vw_book_availability AS
SELECT 
    b.book_id,
    b.isbn,
    b.title,
    b.author,
    b.category,
    b.total_copies,
    b.available_copies,
    (b.total_copies - b.available_copies) AS issued_copies
FROM books b;

-- View: User fines summary
CREATE OR REPLACE VIEW vw_user_fines AS
SELECT 
    u.user_id,
    u.username,
    u.full_name,
    SUM(CASE WHEN f.status = 'pending' THEN f.amount ELSE 0 END) AS pending_fines,
    SUM(CASE WHEN f.status = 'paid' THEN f.amount ELSE 0 END) AS paid_fines,
    COUNT(f.fine_id) AS total_fines
FROM users u
LEFT JOIN fines f ON u.user_id = f.user_id
GROUP BY u.user_id, u.username, u.full_name;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
