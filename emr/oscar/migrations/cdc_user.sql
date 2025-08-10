-- Create the CDC user (password can be replaced with env var at runtime)
CREATE USER IF NOT EXISTS 'cdc_user'@'%' IDENTIFIED BY 'cdc_pass';

-- Grant privileges required for reading binary logs
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'cdc_user'@'%';

-- (Optional) For debugging information_schema etc.
GRANT SELECT ON performance_schema.* TO 'cdc_user'@'%';

-- Persist privileges
FLUSH PRIVILEGES;
