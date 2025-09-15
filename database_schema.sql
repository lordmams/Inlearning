-- =====================================================
-- SCHÉMA DE BASE DE DONNÉES - PLATEFORME E-LEARNING
-- Annexe B - Exemple d'interrogation & pipeline SQL
-- =====================================================

-- B.1 Schéma minimal (PostgreSQL)

-- Utilisateurs
CREATE TABLE users (
  user_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email        TEXT UNIQUE NOT NULL,
  full_name    TEXT,
  age          INTEGER,
  gender       TEXT,
  preferred_language TEXT,
  learning_mode TEXT,
  highest_academic_level TEXT,
  total_experience_years DECIMAL(4,1),
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- Centres d'intérêt (N:N)
CREATE TABLE interests (
  interest_id  SERIAL PRIMARY KEY,
  label        TEXT UNIQUE NOT NULL,
  category     TEXT, -- 'tech', 'business', 'creative', etc.
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_interests (
  user_id     UUID REFERENCES users(user_id) ON DELETE CASCADE,
  interest_id INT  REFERENCES interests(interest_id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, interest_id)
);

-- Objectifs des utilisateurs
CREATE TABLE goals (
  goal_id      SERIAL PRIMARY KEY,
  label        TEXT NOT NULL,
  type         TEXT CHECK (type IN ('short_term', 'long_term')),
  category     TEXT, -- 'career', 'skill', 'project', etc.
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_goals (
  user_id      UUID REFERENCES users(user_id) ON DELETE CASCADE,
  goal_id      INT  REFERENCES goals(goal_id) ON DELETE CASCADE,
  priority     INTEGER DEFAULT 1,
  created_at   TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, goal_id)
);

-- Historique d'usage (logs front)
CREATE TABLE usage_logs (
  log_id       BIGSERIAL PRIMARY KEY,
  user_id      UUID REFERENCES users(user_id),
  resource_id  TEXT,           -- id du cours/ressource
  action       TEXT,           -- 'view' | 'click' | 'complete' | 'start' | 'pause'
  session_id   TEXT,           -- identifiant de session
  ts           TIMESTAMPTZ DEFAULT now(),
  metadata     JSONB           -- données additionnelles (durée, progression, etc.)
);

-- Segments d'apprenants (résultat du clustering)
CREATE TABLE user_segments (
  user_id      UUID REFERENCES users(user_id) ON DELETE CASCADE,
  segment_id   INTEGER NOT NULL,
  confidence   DECIMAL(3,2) DEFAULT 1.0, -- confiance du clustering
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id)
);

-- Métriques d'ambition calculées
CREATE TABLE ambition_metrics (
  user_id      UUID REFERENCES users(user_id) ON DELETE CASCADE,
  short_term_goals_count INTEGER DEFAULT 0,
  long_term_goals_count  INTEGER DEFAULT 0,
  ambition_score         INTEGER DEFAULT 0,
  engagement_level       TEXT, -- 'low', 'medium', 'high'
  last_calculated        TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id)
);

-- =====================================================
-- INDEX POUR OPTIMISATION DES PERFORMANCES
-- =====================================================

-- Index sur les logs d'usage
CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_action ON usage_logs(action);
CREATE INDEX idx_usage_logs_ts ON usage_logs(ts);
CREATE INDEX idx_usage_logs_resource ON usage_logs(resource_id);

-- Index sur les intérêts utilisateur
CREATE INDEX idx_user_interests_user ON user_interests(user_id);
CREATE INDEX idx_user_interests_interest ON user_interests(interest_id);

-- Index sur les objectifs utilisateur
CREATE INDEX idx_user_goals_user ON user_goals(user_id);
CREATE INDEX idx_user_goals_goal ON user_goals(goal_id);

-- Index sur les segments
CREATE INDEX idx_user_segments_segment ON user_segments(segment_id);

-- =====================================================
-- VUES UTILES POUR L'ANALYSE
-- =====================================================

-- Vue des profils utilisateurs enrichis
CREATE VIEW user_profiles AS
SELECT 
  u.user_id,
  u.email,
  u.full_name,
  u.age,
  u.gender,
  u.preferred_language,
  u.learning_mode,
  u.highest_academic_level,
  u.total_experience_years,
  us.segment_id,
  am.ambition_score,
  am.engagement_level,
  COUNT(DISTINCT ui.interest_id) as interests_count,
  COUNT(DISTINCT CASE WHEN ug.goal_id IN (SELECT goal_id FROM goals WHERE type = 'short_term') THEN ug.goal_id END) as short_term_goals_count,
  COUNT(DISTINCT CASE WHEN ug.goal_id IN (SELECT goal_id FROM goals WHERE type = 'long_term') THEN ug.goal_id END) as long_term_goals_count,
  u.created_at
FROM users u
LEFT JOIN user_segments us ON u.user_id = us.user_id
LEFT JOIN ambition_metrics am ON u.user_id = am.user_id
LEFT JOIN user_interests ui ON u.user_id = ui.user_id
LEFT JOIN user_goals ug ON u.user_id = ug.user_id
GROUP BY u.user_id, us.segment_id, am.ambition_score, am.engagement_level;

-- Vue des statistiques d'usage par ressource
CREATE VIEW resource_stats AS
SELECT 
  resource_id,
  COUNT(*) as total_actions,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(CASE WHEN action = 'view' THEN 1 END) as views,
  COUNT(CASE WHEN action = 'click' THEN 1 END) as clicks,
  COUNT(CASE WHEN action = 'complete' THEN 1 END) as completions,
  ROUND(
    COUNT(CASE WHEN action = 'click' THEN 1 END)::DECIMAL / 
    NULLIF(COUNT(CASE WHEN action = 'view' THEN 1 END), 0) * 100, 2
  ) as ctr_percent
FROM usage_logs
WHERE ts >= now() - INTERVAL '30 days'
GROUP BY resource_id;

-- =====================================================
-- FONCTIONS UTILES
-- =====================================================

-- Fonction pour calculer le score d'ambition d'un utilisateur
CREATE OR REPLACE FUNCTION calculate_ambition_score(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
  short_count INTEGER;
  long_count INTEGER;
BEGIN
  SELECT 
    COUNT(DISTINCT CASE WHEN g.type = 'short_term' THEN ug.goal_id END),
    COUNT(DISTINCT CASE WHEN g.type = 'long_term' THEN ug.goal_id END)
  INTO short_count, long_count
  FROM user_goals ug
  JOIN goals g ON ug.goal_id = g.goal_id
  WHERE ug.user_id = p_user_id;
  
  RETURN short_count + long_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour déterminer le niveau d'engagement
CREATE OR REPLACE FUNCTION get_engagement_level(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
  action_count INTEGER;
  engagement_level TEXT;
BEGIN
  SELECT COUNT(*) INTO action_count
  FROM usage_logs
  WHERE user_id = p_user_id 
    AND ts >= now() - INTERVAL '30 days';
  
  IF action_count >= 50 THEN
    engagement_level := 'high';
  ELSIF action_count >= 20 THEN
    engagement_level := 'medium';
  ELSE
    engagement_level := 'low';
  END IF;
  
  RETURN engagement_level;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS POUR MAINTENIR LA COHÉRENCE
-- =====================================================

-- Trigger pour mettre à jour automatiquement les métriques d'ambition
CREATE OR REPLACE FUNCTION update_ambition_metrics()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO ambition_metrics (user_id, short_term_goals_count, long_term_goals_count, ambition_score)
  VALUES (
    NEW.user_id,
    (SELECT COUNT(*) FROM user_goals ug JOIN goals g ON ug.goal_id = g.goal_id 
     WHERE ug.user_id = NEW.user_id AND g.type = 'short_term'),
    (SELECT COUNT(*) FROM user_goals ug JOIN goals g ON ug.goal_id = g.goal_id 
     WHERE ug.user_id = NEW.user_id AND g.type = 'long_term'),
    calculate_ambition_score(NEW.user_id)
  )
  ON CONFLICT (user_id) DO UPDATE SET
    short_term_goals_count = EXCLUDED.short_term_goals_count,
    long_term_goals_count = EXCLUDED.long_term_goals_count,
    ambition_score = EXCLUDED.ambition_score,
    last_calculated = now();
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_ambition_metrics
  AFTER INSERT OR UPDATE OR DELETE ON user_goals
  FOR EACH ROW EXECUTE FUNCTION update_ambition_metrics();

-- =====================================================
-- COMMENTAIRES SUR LES TABLES
-- =====================================================

COMMENT ON TABLE users IS 'Table principale des utilisateurs de la plateforme e-learning';
COMMENT ON TABLE interests IS 'Catalogue des centres d''intérêt disponibles';
COMMENT ON TABLE user_interests IS 'Relation many-to-many entre utilisateurs et intérêts';
COMMENT ON TABLE goals IS 'Catalogue des objectifs possibles (court/long terme)';
COMMENT ON TABLE user_goals IS 'Objectifs assignés aux utilisateurs';
COMMENT ON TABLE usage_logs IS 'Logs d''activité des utilisateurs sur la plateforme';
COMMENT ON TABLE user_segments IS 'Segments d''apprenants issus du clustering ML';
COMMENT ON TABLE ambition_metrics IS 'Métriques calculées d''ambition et d''engagement';

COMMENT ON COLUMN usage_logs.metadata IS 'Données JSON additionnelles (durée, progression, etc.)';
COMMENT ON COLUMN user_segments.confidence IS 'Niveau de confiance du clustering (0-1)';
COMMENT ON COLUMN ambition_metrics.engagement_level IS 'Niveau d''engagement: low/medium/high'; 