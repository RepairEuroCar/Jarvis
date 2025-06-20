-- PostgreSQL schema for Jarvis knowledge topics
-- Run this after jarvis_users_pg.sql to extend the database

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS ltree;

-- Enumerations for domain and difficulty
DO $$ BEGIN
    CREATE TYPE knowledge_domain AS ENUM (
        'core_python', 'web_dev', 'data_science', 'ai_ml',
        'devops', 'algorithms', 'system_design', 'emerging_tech'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE topic_difficulty AS ENUM (
        'beginner', 'junior', 'intermediate', 'advanced',
        'expert', 'research'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Trigger function for timestamps and knowledge graph updates
CREATE OR REPLACE FUNCTION update_topic_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    IF NEW.parent_topic_id IS DISTINCT FROM OLD.parent_topic_id THEN
        NEW.knowledge_graph_path = (
            SELECT COALESCE(parent.knowledge_graph_path, 'root') || '.' || NEW.topic_id::text
            FROM jarvis_topics parent
            WHERE parent.topic_id = NEW.parent_topic_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Main topics table
CREATE TABLE IF NOT EXISTS jarvis_topics (
    topic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(150) NOT NULL,
    technical_title VARCHAR(150),
    short_description VARCHAR(300),
    full_description TEXT,
    knowledge_domain knowledge_domain NOT NULL,
    knowledge_graph_path LTREE,
    parent_topic_id UUID REFERENCES jarvis_topics(topic_id) ON DELETE SET NULL,
    child_topics UUID[] DEFAULT ARRAY[]::UUID[],
    ai_metadata JSONB NOT NULL DEFAULT '{"embedding_vector": null, "concept_importance": 0.5, "prerequisite_graph": [], "related_concepts": [], "knowledge_components": {"theory": 0, "practice": 0, "memorization": 0, "creativity": 0}}',
    difficulty_level topic_difficulty NOT NULL,
    required_background JSONB DEFAULT '{"python_versions": [], "math_level": 0, "theory_requirements": []}',
    learning_metrics JSONB DEFAULT '{"avg_learning_time_minutes": 0, "success_rate": 0, "common_mistakes": [], "optimal_teaching_approach": null}',
    learning_resources JSONB DEFAULT '{"interactive_examples": [], "video_tutorials": [], "research_papers": [], "official_docs": [], "community_articles": []}',
    applications JSONB DEFAULT '{"common_use_cases": [], "real_world_examples": [], "related_projects": []}',
    technical_implementation JSONB DEFAULT '{"standard_libraries": [], "third_party_packages": [], "performance_considerations": null, "security_implications": null}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_ai_review TIMESTAMPTZ,
    next_review_due TIMESTAMPTZ,
    metadata JSONB DEFAULT '{"verified_by_community": false, "curated_by_experts": false, "controversial_score": 0, "update_frequency": "medium"}'
);

CREATE INDEX IF NOT EXISTS idx_jarvis_topics_domain ON jarvis_topics(knowledge_domain);
CREATE INDEX IF NOT EXISTS idx_jarvis_topics_difficulty ON jarvis_topics(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_jarvis_topics_knowledge_graph ON jarvis_topics USING GIST (knowledge_graph_path);
CREATE INDEX IF NOT EXISTS idx_jarvis_topics_ai_metadata ON jarvis_topics USING GIN (ai_metadata jsonb_path_ops);

CREATE TRIGGER trg_jarvis_topic_update
BEFORE UPDATE ON jarvis_topics
FOR EACH ROW
EXECUTE FUNCTION update_topic_timestamps();

-- Relations between topics
CREATE TABLE IF NOT EXISTS jarvis_topic_relations (
    relation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_topic_id UUID NOT NULL REFERENCES jarvis_topics(topic_id),
    target_topic_id UUID NOT NULL REFERENCES jarvis_topics(topic_id),
    relation_type VARCHAR(50) NOT NULL CHECK (relation_type IN (
        'prerequisite', 'corequisite', 'alternative',
        'composition', 'specialization', 'generalization'
    )),
    strength FLOAT NOT NULL DEFAULT 0.5 CHECK (strength > 0 AND strength <= 1),
    bidirectional BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT no_self_relation CHECK (source_topic_id <> target_topic_id)
);

CREATE INDEX IF NOT EXISTS idx_jarvis_topic_relations_type ON jarvis_topic_relations (source_topic_id, relation_type);

-- Version history for topics
CREATE TABLE IF NOT EXISTS jarvis_topic_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES jarvis_topics(topic_id),
    version_data JSONB NOT NULL,
    version_number VARCHAR(20) NOT NULL,
    change_log TEXT NOT NULL,
    approved_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Helper function to query related topics
CREATE OR REPLACE FUNCTION find_related_topics(
    topic_uuid UUID,
    relation_types VARCHAR[] DEFAULT ARRAY['prerequisite', 'corequisite'],
    min_strength FLOAT DEFAULT 0.3
) RETURNS TABLE (
    related_topic_id UUID,
    relation_type VARCHAR,
    strength FLOAT,
    title VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT tr.target_topic_id, tr.relation_type, tr.strength, t.title
    FROM jarvis_topic_relations tr
    JOIN jarvis_topics t ON tr.target_topic_id = t.topic_id
    WHERE tr.source_topic_id = topic_uuid
      AND tr.relation_type = ANY(relation_types)
      AND tr.strength >= min_strength
    UNION
    SELECT tr.source_topic_id, tr.relation_type, tr.strength, t.title
    FROM jarvis_topic_relations tr
    JOIN jarvis_topics t ON tr.source_topic_id = t.topic_id
    WHERE tr.target_topic_id = topic_uuid
      AND tr.bidirectional = TRUE
      AND tr.relation_type = ANY(relation_types)
      AND tr.strength >= min_strength;
END;
$$ LANGUAGE plpgsql;

-- Materialized view for quickly accessing popular topics
CREATE MATERIALIZED VIEW IF NOT EXISTS jarvis_popular_topics AS
SELECT
    t.topic_id,
    t.title,
    t.knowledge_domain,
    t.difficulty_level,
    jsonb_array_length(t.ai_metadata->'related_concepts') AS related_count,
    t.updated_at
FROM jarvis_topics t
ORDER BY
    (t.learning_metrics->>'success_rate')::FLOAT DESC,
    (t.ai_metadata->>'concept_importance')::FLOAT DESC
LIMIT 100
WITH DATA;

-- Commentary
COMMENT ON TABLE jarvis_topics IS 'Advanced knowledge topics for Jarvis with hierarchical graph support';
COMMENT ON COLUMN jarvis_topics.ai_metadata IS 'AI metadata including embeddings and knowledge components';
COMMENT ON COLUMN jarvis_topics.knowledge_graph_path IS 'Hierarchy path in the knowledge graph';
COMMENT ON COLUMN jarvis_topics.technical_implementation IS 'Implementation details for real projects';
