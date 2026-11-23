-- Night Return - MySQL schema (MySQL 8+)
CREATE DATABASE IF NOT EXISTS night_safety_db CHARACTER SET utf8mb4;
USE night_safety_db;

CREATE TABLE IF NOT EXISTS users (
  user_id        INT AUTO_INCREMENT PRIMARY KEY,
  username       VARCHAR(100) NOT NULL,
  email          VARCHAR(150) NOT NULL UNIQUE,
  phone_number   VARCHAR(15)  NOT NULL UNIQUE,
  address        TEXT,
  password_hash  VARCHAR(100) NOT NULL,          -- BCrypt
  code_word_hash VARCHAR(100),                   -- BCrypt of normalised code word
  profile_pictures MEDIUMTEXT,                   -- JSON array of small base64 JPEGs
  is_verified    BOOLEAN DEFAULT TRUE,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emergency_contacts (
  contact_id     INT AUTO_INCREMENT PRIMARY KEY,
  user_id        INT NOT NULL,
  contact_name   VARCHAR(100) NOT NULL,
  contact_phone  VARCHAR(15)  NOT NULL,
  is_verified    BOOLEAN DEFAULT TRUE,
  priority_order INT DEFAULT 1,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS journeys (
  journey_id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id         INT NOT NULL,
  starting_point  VARCHAR(255) NOT NULL,
  ending_point    VARCHAR(255) NOT NULL,
  transport_mode  ENUM('bus','cab_bike','walk') NOT NULL,
  timer_duration  INT NOT NULL,                  -- minutes (current, after extensions)
  expected_route  MEDIUMTEXT,                    -- JSON polyline [[lat,lng],...]
  status          ENUM('active','completed','alert_triggered','cancelled') DEFAULT 'active',
  started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ended_at        TIMESTAMP NULL,
  deadline        TIMESTAMP NULL,                -- server-side timer end, checked by Watchdog
  off_route_since TIMESTAMP NULL,                -- set when the phone reports off-route
  last_seen       TIMESTAMP NULL,                -- last location heartbeat from the phone
  offline_alerted BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS journey_tracking (
  tracking_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  journey_id   INT NOT NULL,
  latitude     DECIMAL(10,7) NOT NULL,
  longitude    DECIMAL(10,7) NOT NULL,
  is_offline   BOOLEAN DEFAULT FALSE,
  recorded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (journey_id) REFERENCES journeys(journey_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
  alert_id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  journey_id    INT NULL,
  alert_type    ENUM('timer_expired','off_route','code_word_triggered','emergency_button','offline_mode') NOT NULL,
  latitude      DECIMAL(10,7) NULL,
  longitude     DECIMAL(10,7) NULL,
  triggered_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at   TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (journey_id) REFERENCES journeys(journey_id) ON DELETE SET NULL
);

-- Server-side OTPs only. The code is stored as a BCrypt hash, never sent to the browser.
CREATE TABLE IF NOT EXISTS otp_codes (
  otp_id      INT AUTO_INCREMENT PRIMARY KEY,
  phone       VARCHAR(15) NOT NULL,
  purpose     VARCHAR(30) NOT NULL,
  code_hash   VARCHAR(100) NOT NULL,
  attempts    INT DEFAULT 0,
  expires_at  TIMESTAMP NOT NULL,
  INDEX idx_phone_purpose (phone, purpose)
);

-- Every OTP request is logged here so the server can rate-limit by phone and by IP.
CREATE TABLE IF NOT EXISTS otp_requests (
  request_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
  phone        VARCHAR(15) NOT NULL,
  ip           VARCHAR(45) NOT NULL,
  requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_phone_time (phone, requested_at),
  INDEX idx_ip_time (ip, requested_at)
);

-- Records a phone that passed OTP. Registration and contact saving check this on the server.
CREATE TABLE IF NOT EXISTS phone_verifications (
  phone        VARCHAR(15) NOT NULL,
  purpose      VARCHAR(30) NOT NULL,              -- 'registration' or 'contact'
  user_id      INT NULL,
  verified_at  TIMESTAMP NOT NULL,
  PRIMARY KEY (phone, purpose)
);
