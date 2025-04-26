/*
  Warnings:

  - Added the required column `user_name` to the `Game` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE `Game` ADD COLUMN `user_name` VARCHAR(50) NOT NULL;
