CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_category_id ON tickets(category_id);
CREATE INDEX IF NOT EXISTS idx_tickets_agent_id ON tickets(agent_id);
CREATE INDEX IF NOT EXISTS idx_tickets_escalation ON tickets(escalation_flag);
CREATE INDEX IF NOT EXISTS idx_tickets_root_cause ON tickets(root_cause);
CREATE INDEX IF NOT EXISTS idx_agents_shift ON agents(shift);
CREATE INDEX IF NOT EXISTS idx_categories_name_subcategory ON categories(category_name, subcategory);

