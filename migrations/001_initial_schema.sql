-- API Migration Orchestrator - Initial Database Schema
-- PostgreSQL schema for tracking 1500+ APIs and migration state

-- Enable UUID extension for generating unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- API Inventory Table
-- Stores discovered APIs from all platforms
-- ============================================================
CREATE TABLE apis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_name VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,  -- apic, mulesoft, kafka, swagger
    
    -- Ownership metadata
    owner_team VARCHAR(100),
    owner_domain VARCHAR(100),
    owner_component VARCHAR(100),
    owner_contact VARCHAR(255),
    
    -- API metadata
    base_path VARCHAR(500),
    version VARCHAR(50),
    description TEXT,
    tags TEXT[],  -- Array of tags
    
    -- Legacy platform details (JSONB for flexibility)
    legacy_metadata JSONB,
    
    -- Risk scoring
    risk_level VARCHAR(20),  -- LOW, MEDIUM, HIGH, CRITICAL
    risk_score NUMERIC(3, 2),  -- 0.00 to 1.00
    business_criticality VARCHAR(20),  -- LOW, MEDIUM, HIGH, CRITICAL
    
    -- Traffic metrics
    avg_requests_per_day INTEGER,
    avg_latency_ms INTEGER,
    error_rate NUMERIC(5, 4),  -- 0.0000 to 1.0000
    
    -- Discovery metadata
    discovered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    discovered_by VARCHAR(100),  -- Team that discovered it
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: same API name on same platform
    CONSTRAINT unique_api_platform UNIQUE (api_name, platform)
);

-- Indexes for performance with 1500+ APIs
CREATE INDEX idx_apis_owner_team ON apis(owner_team);
CREATE INDEX idx_apis_owner_domain ON apis(owner_domain);
CREATE INDEX idx_apis_platform ON apis(platform);
CREATE INDEX idx_apis_risk_level ON apis(risk_level);
CREATE INDEX idx_apis_tags ON apis USING GIN(tags);  -- GIN index for array searches
CREATE INDEX idx_apis_discovered_at ON apis(discovered_at);

-- ============================================================
-- Migration State Table
-- Tracks migration progress per API
-- ============================================================
CREATE TYPE migration_status AS ENUM (
    'DISCOVERED',          -- API discovered but not planned
    'PLANNED',             -- Migration plan generated
    'VALIDATED',           -- Config validated
    'DEPLOYED_MIRROR',     -- Deployed with traffic mirroring
    'CANARY_5',            -- 5% traffic shifted
    'CANARY_25',           -- 25% traffic shifted
    'CANARY_50',           -- 50% traffic shifted
    'CANARY_75',           -- 75% traffic shifted
    'COMPLETED',           -- 100% traffic shifted
    'ROLLED_BACK',         -- Rolled back to legacy
    'DECOMMISSIONED',      -- Legacy gateway decommissioned
    'FAILED'               -- Migration failed
);

CREATE TABLE migration_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    
    -- Current state
    status migration_status NOT NULL DEFAULT 'DISCOVERED',
    previous_status migration_status,
    
    -- Gloo Gateway details
    gloo_namespace VARCHAR(100),
    gloo_virtual_service_name VARCHAR(255),
    gloo_configs JSONB,  -- Generated Gloo Gateway configs
    
    -- Traffic shifting
    current_traffic_percentage INTEGER DEFAULT 0,
    target_traffic_percentage INTEGER,
    
    -- Metrics comparison (legacy vs Gloo)
    mirror_start_time TIMESTAMP,
    mirror_duration_hours INTEGER,
    legacy_error_rate NUMERIC(5, 4),
    gloo_error_rate NUMERIC(5, 4),
    legacy_p95_latency_ms INTEGER,
    gloo_p95_latency_ms INTEGER,
    payload_mismatches INTEGER DEFAULT 0,
    
    -- State transitions
    last_transition_at TIMESTAMP NOT NULL DEFAULT NOW(),
    transition_reason TEXT,
    
    -- Lock information (for distributed locking)
    locked_by VARCHAR(100),  -- Team that owns the lock
    locked_at TIMESTAMP,
    lock_expires_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- One migration state per API
    CONSTRAINT unique_api_migration UNIQUE (api_id)
);

-- Indexes
CREATE INDEX idx_migration_state_api_id ON migration_state(api_id);
CREATE INDEX idx_migration_state_status ON migration_state(status);
CREATE INDEX idx_migration_state_locked_by ON migration_state(locked_by);
CREATE INDEX idx_migration_state_lock_expires ON migration_state(lock_expires_at);

-- ============================================================
-- Migration Plans Table
-- Stores generated Gloo Gateway configurations
-- ============================================================
CREATE TABLE migration_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    
    -- Plan metadata
    plan_version INTEGER NOT NULL DEFAULT 1,
    generated_by VARCHAR(100) NOT NULL,  -- Team that generated the plan
    
    -- Generated configs
    virtual_service_yaml TEXT,
    route_table_yaml TEXT,
    auth_config_yaml TEXT,
    rate_limit_config_yaml TEXT,
    upstream_yaml TEXT,
    
    -- Validation results
    is_validated BOOLEAN DEFAULT FALSE,
    validation_errors JSONB,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_migration_plans_api_id ON migration_plans(api_id);
CREATE INDEX idx_migration_plans_validated ON migration_plans(is_validated);

-- ============================================================
-- Traffic Metrics Table
-- Historical traffic comparison data
-- ============================================================
CREATE TABLE traffic_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    
    -- Timestamp
    measured_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Traffic percentage at time of measurement
    traffic_percentage INTEGER NOT NULL,
    
    -- Legacy gateway metrics
    legacy_requests_per_sec NUMERIC(10, 2),
    legacy_error_count INTEGER,
    legacy_error_rate NUMERIC(5, 4),
    legacy_p50_latency_ms INTEGER,
    legacy_p95_latency_ms INTEGER,
    legacy_p99_latency_ms INTEGER,
    
    -- Gloo Gateway metrics
    gloo_requests_per_sec NUMERIC(10, 2),
    gloo_error_count INTEGER,
    gloo_error_rate NUMERIC(5, 4),
    gloo_p50_latency_ms INTEGER,
    gloo_p95_latency_ms INTEGER,
    gloo_p99_latency_ms INTEGER,
    
    -- Comparison results
    latency_diff_ms INTEGER,  -- Gloo - Legacy latency
    error_rate_diff NUMERIC(5, 4),
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for time-series queries
CREATE INDEX idx_traffic_metrics_api_id ON traffic_metrics(api_id);
CREATE INDEX idx_traffic_metrics_measured_at ON traffic_metrics(measured_at DESC);
CREATE INDEX idx_traffic_metrics_api_time ON traffic_metrics(api_id, measured_at DESC);

-- ============================================================
-- Approvals Table
-- Human approval records for traffic shifting
-- ============================================================
CREATE TYPE approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');

CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    
    -- Approval request
    request_type VARCHAR(50) NOT NULL,  -- DEPLOY, SHIFT_5, SHIFT_25, etc.
    requester VARCHAR(100) NOT NULL,  -- Team requesting approval
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Request details
    from_status migration_status,
    to_status migration_status NOT NULL,
    traffic_percentage INTEGER,
    justification TEXT,
    
    -- Approval decision
    status approval_status NOT NULL DEFAULT 'PENDING',
    approver VARCHAR(100),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    
    -- Supporting data for decision
    metrics_summary JSONB,  -- Latest metrics snapshot
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approvals_api_id ON approvals(api_id);
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_requested_at ON approvals(requested_at DESC);

-- ============================================================
-- Audit Log Table
-- Immutable audit trail for compliance
-- ============================================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Correlation for tracing
    correlation_id UUID NOT NULL,
    
    -- Actor
    actor VARCHAR(100) NOT NULL,  -- User or team performing action
    actor_team VARCHAR(100),
    
    -- Action details
    action VARCHAR(100) NOT NULL,  -- DISCOVER, PLAN, DEPLOY, SHIFT, ROLLBACK, etc.
    resource_type VARCHAR(50) NOT NULL,  -- API, MIGRATION, APPROVAL, etc.
    resource_id UUID,
    api_name VARCHAR(255),
    platform VARCHAR(50),
    
    -- Action metadata
    details JSONB,  -- Additional action-specific data
    
    -- Result
    success BOOLEAN NOT NULL,
    error_message TEXT,
    
    -- Timestamp (immutable)
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX idx_audit_log_actor ON audit_log(actor);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_api ON audit_log(api_name, platform);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_correlation_id ON audit_log(correlation_id);

-- ============================================================
-- Migration Statistics View
-- Aggregated statistics for monitoring
-- ============================================================
CREATE VIEW migration_statistics AS
SELECT 
    a.owner_team,
    a.owner_domain,
    a.platform,
    COUNT(*) as total_apis,
    COUNT(*) FILTER (WHERE ms.status = 'DISCOVERED') as discovered,
    COUNT(*) FILTER (WHERE ms.status = 'PLANNED') as planned,
    COUNT(*) FILTER (WHERE ms.status = 'VALIDATED') as validated,
    COUNT(*) FILTER (WHERE ms.status LIKE 'CANARY_%') as in_migration,
    COUNT(*) FILTER (WHERE ms.status = 'COMPLETED') as completed,
    COUNT(*) FILTER (WHERE ms.status = 'FAILED') as failed,
    COUNT(*) FILTER (WHERE ms.status = 'ROLLED_BACK') as rolled_back,
    AVG(a.risk_score) as avg_risk_score
FROM apis a
LEFT JOIN migration_state ms ON a.id = ms.api_id
GROUP BY a.owner_team, a.owner_domain, a.platform;

-- ============================================================
-- Helper Functions
-- ============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_apis_updated_at BEFORE UPDATE ON apis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_migration_state_updated_at BEFORE UPDATE ON migration_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_migration_plans_updated_at BEFORE UPDATE ON migration_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_approvals_updated_at BEFORE UPDATE ON approvals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Sample Data for Testing (Optional - comment out for production)
-- ============================================================

-- Insert sample teams and APIs
-- INSERT INTO apis (api_name, platform, owner_team, owner_domain, risk_level, tags)
-- VALUES 
--     ('payment-gateway-api', 'apic', 'payments-team', 'payment-services', 'HIGH', ARRAY['payment', 'core']),
--     ('checkout-api-v2', 'apic', 'payments-team', 'payment-services', 'MEDIUM', ARRAY['checkout', 'payment']),
--     ('customer-profile-api', 'mulesoft', 'customer-team', 'customer-services', 'MEDIUM', ARRAY['customer', 'profile']);

COMMIT;
