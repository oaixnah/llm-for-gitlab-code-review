-- 初始化数据库脚本
-- 用于 Docker 容器启动时自动创建数据库结构

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS llm_review CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE llm_review;

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'llm_user'@'%' IDENTIFIED BY 'llm_password';
GRANT ALL PRIVILEGES ON llm_review.* TO 'llm_user'@'%';
FLUSH PRIVILEGES;

-- 创建表结构（这些表会由 SQLAlchemy 自动创建，这里只是作为备份）

-- Reviews 表
CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    merge_request_iid INT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_review (project_id, merge_request_iid),
    INDEX idx_project_mr (project_id, merge_request_iid),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Review Discussions 表
CREATE TABLE IF NOT EXISTS review_discussions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    review_id INT NOT NULL,
    discussion_id VARCHAR(255) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    line_number INT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
    UNIQUE KEY unique_discussion (review_id, discussion_id),
    INDEX idx_review_id (review_id),
    INDEX idx_file_path (file_path(255)),
    INDEX idx_discussion_id (discussion_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Review File Records 表
CREATE TABLE IF NOT EXISTS review_file_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    review_id INT NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    diff_content LONGTEXT,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
    UNIQUE KEY unique_file_record (review_id, file_path),
    INDEX idx_review_id (review_id),
    INDEX idx_file_path (file_path(255)),
    INDEX idx_processed (processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Review File LLM Messages 表
CREATE TABLE IF NOT EXISTS review_file_llm_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_record_id INT NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    tokens_used INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_record_id) REFERENCES review_file_records(id) ON DELETE CASCADE,
    INDEX idx_file_record_id (file_record_id),
    INDEX idx_message_type (message_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入一些示例数据（可选）
-- INSERT INTO reviews (project_id, merge_request_iid, status) VALUES (1, 1, 'pending');

-- 创建视图（可选）
CREATE OR REPLACE VIEW review_summary AS
SELECT 
    r.id,
    r.project_id,
    r.merge_request_iid,
    r.status,
    r.created_at,
    COUNT(DISTINCT rd.id) as discussion_count,
    COUNT(DISTINCT rfr.id) as file_count,
    SUM(CASE WHEN rfr.processed = TRUE THEN 1 ELSE 0 END) as processed_files
FROM reviews r
LEFT JOIN review_discussions rd ON r.id = rd.review_id
LEFT JOIN review_file_records rfr ON r.id = rfr.review_id
GROUP BY r.id, r.project_id, r.merge_request_iid, r.status, r.created_at;

-- 创建存储过程（可选）
DELIMITER //

CREATE PROCEDURE IF NOT EXISTS CleanupOldReviews(IN days_old INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- 删除超过指定天数的已完成审查记录
    DELETE FROM reviews 
    WHERE status IN ('completed', 'cancelled') 
    AND created_at < DATE_SUB(NOW(), INTERVAL days_old DAY);
    
    COMMIT;
END //

DELIMITER ;

-- 创建触发器（可选）
DELIMITER //

CREATE TRIGGER IF NOT EXISTS update_review_status
AFTER UPDATE ON review_file_records
FOR EACH ROW
BEGIN
    DECLARE total_files INT DEFAULT 0;
    DECLARE processed_files INT DEFAULT 0;
    
    -- 计算总文件数和已处理文件数
    SELECT COUNT(*), SUM(CASE WHEN processed = TRUE THEN 1 ELSE 0 END)
    INTO total_files, processed_files
    FROM review_file_records
    WHERE review_id = NEW.review_id;
    
    -- 如果所有文件都已处理，更新审查状态
    IF total_files > 0 AND processed_files = total_files THEN
        UPDATE reviews 
        SET status = 'completed', updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.review_id AND status = 'pending';
    END IF;
END //

DELIMITER ;

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_reviews_status_created ON reviews(status, created_at);
CREATE INDEX IF NOT EXISTS idx_discussions_file_line ON review_discussions(file_path(255), line_number);
CREATE INDEX IF NOT EXISTS idx_file_records_change_type ON review_file_records(change_type, processed);

-- 设置数据库参数
SET GLOBAL innodb_buffer_pool_size = 268435456; -- 256MB
SET GLOBAL max_connections = 200;
SET GLOBAL query_cache_size = 67108864; -- 64MB

-- 显示创建结果
SHOW TABLES;
SELECT 'Database initialization completed successfully' AS status;