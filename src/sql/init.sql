CREATE SCHEMA IF NOT EXISTS "dialogue_assistant";

ALTER DATABASE mydb SET timezone TO 'Europe/Moscow';
SELECT pg_reload_conf(); 

CREATE TABLE IF NOT EXISTS "User" (
    id SERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);