-- Idempotent SQL to add annual_leave_allocation to `user` table
-- MySQL 8+ supports IF NOT EXISTS for ADD COLUMN
ALTER TABLE `user`
  ADD COLUMN IF NOT EXISTS `annual_leave_allocation` INT NOT NULL DEFAULT 30;
