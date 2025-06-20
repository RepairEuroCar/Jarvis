-- PostgreSQL schema for knowledge topics used by Jarvis
-- Run this file to create the tables storing topics and related metadata

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enum type for topic difficulty
CREATE TYPE IF NOT EXISTS difficulty_level AS ENUM (
    'beginner', 'easy', 'medium', 'hard', 'expert', 'research'
);

-- Update trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Main topics table
CREATE TABLE IF NOT EXISTS jarvis_topics (
    topic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(150) NOT NULL,
    description TEXT,
    detailed_technical_description TEXT,
    difficulty difficulty_level NOT NULL,
    parent_topic_id UUID REFERENCES jarvis_topics(topic_id) ON DELETE CASCADE,
    order_in_sequence INTEGER NOT NULL CHECK (order_in_sequence >= 0),
    ai_learning_priority INTEGER DEFAULT 50 CHECK (ai_learning_priority BETWEEN 1 AND 100),
    ai_relevance_score FLOAT DEFAULT 0.5,
    ai_prerequisites UUID[],
    ai_related_skills UUID[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_ai_training_time TIMESTAMPTZ,
    average_learning_time INTERVAL,
    success_rate FLOAT CHECK (success_rate >= 0 AND success_rate <= 1),
    reference_materials JSONB,
    interactive_examples JSONB,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(description, ''))
    ) STORED,
    CONSTRAINT unique_title_parent UNIQUE (title, parent_topic_id)
);

CREATE INDEX IF NOT EXISTS idx_topics_parent ON jarvis_topics(parent_topic_id);
CREATE INDEX IF NOT EXISTS idx_topics_search ON jarvis_topics USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_ai_prerequisites ON jarvis_topics USING GIN (ai_prerequisites);
CREATE INDEX IF NOT EXISTS idx_ai_related_skills ON jarvis_topics USING GIN (ai_related_skills);

CREATE TRIGGER trg_topics_updated
BEFORE UPDATE ON jarvis_topics
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Relationships between topics and other entities
CREATE TABLE IF NOT EXISTS jarvis_topic_relations (
    relation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES jarvis_topics(topic_id) ON DELETE CASCADE,
    related_entity_type VARCHAR(50) NOT NULL CHECK (
        related_entity_type IN ('skill', 'project', 'tool', 'concept', 'algorithm')
    ),
    related_entity_id UUID NOT NULL,
    relation_strength FLOAT DEFAULT 1.0 CHECK (relation_strength > 0 AND relation_strength <= 1.0),
    relation_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topic_relations_type ON jarvis_topic_relations(topic_id, related_entity_type);

-- History of changes to topics
CREATE TABLE IF NOT EXISTS jarvis_topic_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES jarvis_topics(topic_id) ON DELETE CASCADE,
    changed_fields JSONB NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

