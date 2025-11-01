-- Migration: Add order completion tracking fields
-- Date: 2025-11-01
-- Description: Add fields for tracking order completion confirmation from both parties

-- Add new columns to orders table
ALTER TABLE orders ADD COLUMN customer_confirmed BOOLEAN DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN driver_confirmed BOOLEAN DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN cancelled_by INTEGER NULL;  -- user_id who cancelled
ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP NULL;

-- Update status enum to include 'in_progress' and 'closed'
-- Note: SQLite doesn't support ALTER COLUMN, so we need to handle this in code
-- Status values: 'active', 'in_progress', 'completed', 'cancelled', 'closed', 'no_offers'
