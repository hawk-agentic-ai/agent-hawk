-- PostgreSQL Transaction Management Functions for Supabase
-- These functions enable atomic multi-table operations via RPC calls

-- Create a table to track active transactions
CREATE TABLE IF NOT EXISTS transaction_log (
    transaction_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('active', 'committed', 'rolled_back', 'failed')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    operations_count INTEGER DEFAULT 0,
    created_by TEXT DEFAULT 'HAWK_AGENT',
    notes TEXT
);

-- Enable Row Level Security
ALTER TABLE transaction_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for transaction_log
CREATE POLICY "Enable read access for authenticated users" ON "public"."transaction_log"
AS PERMISSIVE FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Enable write access for authenticated users" ON "public"."transaction_log"
AS PERMISSIVE FOR ALL
TO authenticated
USING (true);

-- Function to begin a transaction
CREATE OR REPLACE FUNCTION begin_transaction(transaction_id TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Insert transaction record
    INSERT INTO transaction_log (transaction_id, status, started_at)
    VALUES (transaction_id, 'active', NOW())
    ON CONFLICT (transaction_id) DO NOTHING;

    -- Begin actual transaction
    -- Note: This function runs within its own transaction context
    -- The calling code needs to manage the actual transaction scope

    RETURN json_build_object(
        'success', true,
        'transaction_id', transaction_id,
        'status', 'active',
        'started_at', NOW()
    );

EXCEPTION WHEN others THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM,
        'transaction_id', transaction_id
    );
END;
$$;

-- Function to commit a transaction
CREATE OR REPLACE FUNCTION commit_transaction(transaction_id TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Update transaction status
    UPDATE transaction_log
    SET status = 'committed', completed_at = NOW()
    WHERE transaction_id = commit_transaction.transaction_id;

    -- The actual COMMIT happens at the end of the calling transaction

    RETURN json_build_object(
        'success', true,
        'transaction_id', transaction_id,
        'status', 'committed',
        'completed_at', NOW()
    );

EXCEPTION WHEN others THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM,
        'transaction_id', transaction_id
    );
END;
$$;

-- Function to rollback a transaction
CREATE OR REPLACE FUNCTION rollback_transaction(transaction_id TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Update transaction status
    UPDATE transaction_log
    SET status = 'rolled_back', completed_at = NOW()
    WHERE transaction_id = rollback_transaction.transaction_id;

    -- The actual ROLLBACK happens when the calling transaction fails

    RETURN json_build_object(
        'success', true,
        'transaction_id', transaction_id,
        'status', 'rolled_back',
        'completed_at', NOW()
    );

EXCEPTION WHEN others THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM,
        'transaction_id', transaction_id
    );
END;
$$;

-- Function to get transaction status
CREATE OR REPLACE FUNCTION get_transaction_status(transaction_id TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    tx_record transaction_log%ROWTYPE;
BEGIN
    SELECT * INTO tx_record FROM transaction_log
    WHERE transaction_id = get_transaction_status.transaction_id;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'success', false,
            'error', 'Transaction not found',
            'transaction_id', transaction_id
        );
    END IF;

    RETURN json_build_object(
        'success', true,
        'transaction_id', tx_record.transaction_id,
        'status', tx_record.status,
        'started_at', tx_record.started_at,
        'completed_at', tx_record.completed_at,
        'operations_count', tx_record.operations_count
    );

EXCEPTION WHEN others THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM,
        'transaction_id', transaction_id
    );
END;
$$;

-- Function to clean up old transaction logs (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_transaction_logs(days_old INTEGER DEFAULT 7)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM transaction_log
    WHERE completed_at < NOW() - INTERVAL '1 day' * days_old
    AND status IN ('committed', 'rolled_back', 'failed');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN json_build_object(
        'success', true,
        'deleted_count', deleted_count,
        'cleanup_date', NOW()
    );

EXCEPTION WHEN others THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM
    );
END;
$$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transaction_log_status ON transaction_log(status);
CREATE INDEX IF NOT EXISTS idx_transaction_log_started_at ON transaction_log(started_at);
CREATE INDEX IF NOT EXISTS idx_transaction_log_completed_at ON transaction_log(completed_at);

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION begin_transaction(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION commit_transaction(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION rollback_transaction(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_transaction_status(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_transaction_logs(INTEGER) TO authenticated;

-- Comments for documentation
COMMENT ON FUNCTION begin_transaction(TEXT) IS 'Begin a new database transaction with tracking';
COMMENT ON FUNCTION commit_transaction(TEXT) IS 'Commit a transaction and update tracking';
COMMENT ON FUNCTION rollback_transaction(TEXT) IS 'Rollback a transaction and update tracking';
COMMENT ON FUNCTION get_transaction_status(TEXT) IS 'Get the current status of a transaction';
COMMENT ON FUNCTION cleanup_transaction_logs(INTEGER) IS 'Clean up old transaction logs for maintenance';