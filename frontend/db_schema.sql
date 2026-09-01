-- =========================================================
-- DATABASE SETTINGS
-- =========================================================

SET NAMES utf8mb4;
SET time_zone = '+10:00';


-- =========================================================
-- 1. USERS
-- =========================================================

CREATE TABLE users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    name VARCHAR(150) NOT NULL,

    email VARCHAR(255) NOT NULL,

    password VARCHAR(255) NOT NULL,

    profile_pic TEXT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    UNIQUE KEY uq_users_email (email)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 2. CHATS
-- =========================================================

CREATE TABLE chats (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    user_id BIGINT UNSIGNED NOT NULL,

    title VARCHAR(255) NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    CONSTRAINT fk_chats_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    INDEX idx_chats_user_updated_at (
        user_id,
        updated_at DESC
    )

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 3. MESSAGES
-- =========================================================

CREATE TABLE messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    chat_id BIGINT UNSIGNED NOT NULL,

    role ENUM(
        'system',
        'user'
    ) NOT NULL,

    content_type ENUM(
        'text',
        'image',
        'video',
        'link',
        'file',
        'other'
    ) NOT NULL DEFAULT 'text',

    content LONGTEXT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    CONSTRAINT fk_messages_chat
        FOREIGN KEY (chat_id)
        REFERENCES chats(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    INDEX idx_messages_chat_created_at (
        chat_id,
        created_at
    ),

    INDEX idx_messages_chat_role (
        chat_id,
        role
    )

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 4. MESSAGE ATTACHMENTS
-- =========================================================

CREATE TABLE message_attachments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    message_id BIGINT UNSIGNED NOT NULL,

    name VARCHAR(255) NOT NULL,

    path TEXT NOT NULL,

    type VARCHAR(100) NULL,

    size BIGINT UNSIGNED NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    CONSTRAINT fk_message_attachments_message
        FOREIGN KEY (message_id)
        REFERENCES messages(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    INDEX idx_message_attachments_message_id (
        message_id
    ),

    INDEX idx_message_attachments_type (
        type
    )

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;