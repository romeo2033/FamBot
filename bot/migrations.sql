CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        TEXT,
    first_name      TEXT,
    last_name       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pairs (
    id                  SERIAL PRIMARY KEY,
    creator_user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    partner_user_id     INT REFERENCES users(id) ON DELETE SET NULL,
    invite_token        VARCHAR(64) UNIQUE NOT NULL,
    start_date          DATE,
    cloud_drive_url     TEXT,
    last_milestone_days INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wishlist_items (
    id              SERIAL PRIMARY KEY,
    pair_id         INT NOT NULL REFERENCES pairs(id) ON DELETE CASCADE,
    owner_user_id   INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    is_done         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications_log (
    id              SERIAL PRIMARY KEY,
    pair_id         INT NOT NULL REFERENCES pairs(id) ON DELETE CASCADE,
    notif_type      TEXT NOT NULL,
    payload         JSONB,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);