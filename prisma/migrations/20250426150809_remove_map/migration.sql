/*
  Warnings:

  - You are about to drop the column `created_at` on the `AdviceRequest` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `AdviceRequest` table. All the data in the column will be lost.
  - You are about to drop the column `used_count` on the `AdviceRequest` table. All the data in the column will be lost.
  - You are about to drop the column `added_at` on the `BuildQueue` table. All the data in the column will be lost.
  - You are about to drop the column `building_id` on the `BuildQueue` table. All the data in the column will be lost.
  - You are about to drop the column `city_id` on the `BuildQueue` table. All the data in the column will be lost.
  - You are about to drop the column `queue_position` on the `BuildQueue` table. All the data in the column will be lost.
  - You are about to drop the column `build_time` on the `Building` table. All the data in the column will be lost.
  - You are about to drop the column `maintenance_cost` on the `Building` table. All the data in the column will be lost.
  - You are about to drop the column `prerequisite_tech_id` on the `Building` table. All the data in the column will be lost.
  - You are about to drop the column `resource_cost` on the `Building` table. All the data in the column will be lost.
  - You are about to drop the column `created_turn` on the `City` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `City` table. All the data in the column will be lost.
  - You are about to drop the column `leader_name` on the `CivType` table. All the data in the column will be lost.
  - You are about to drop the column `action_type` on the `DiplomacyAction` table. All the data in the column will be lost.
  - You are about to drop the column `new_score` on the `DiplomacyAction` table. All the data in the column will be lost.
  - You are about to drop the column `session_id` on the `DiplomacyAction` table. All the data in the column will be lost.
  - The primary key for the `DiplomacySession` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the column `ai_civ_id` on the `DiplomacySession` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `DiplomacySession` table. All the data in the column will be lost.
  - You are about to drop the column `relationship_score` on the `DiplomacySession` table. All the data in the column will be lost.
  - You are about to drop the column `session_id` on the `DiplomacySession` table. All the data in the column will be lost.
  - You are about to drop the column `created_at` on the `Game` table. All the data in the column will be lost.
  - You are about to drop the column `map_radius` on the `Game` table. All the data in the column will be lost.
  - You are about to drop the column `turn_limit` on the `Game` table. All the data in the column will be lost.
  - You are about to drop the column `user_name` on the `Game` table. All the data in the column will be lost.
  - You are about to drop the column `civ_type_id` on the `GameCiv` table. All the data in the column will be lost.
  - You are about to drop the column `game_id` on the `GameCiv` table. All the data in the column will be lost.
  - You are about to drop the column `is_player` on the `GameCiv` table. All the data in the column will be lost.
  - You are about to drop the column `start_q` on the `GameCiv` table. All the data in the column will be lost.
  - You are about to drop the column `start_r` on the `GameCiv` table. All the data in the column will be lost.
  - You are about to drop the column `completed_at` on the `GameCivTechnology` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `GameCivTechnology` table. All the data in the column will be lost.
  - You are about to drop the column `progress_points` on the `GameCivTechnology` table. All the data in the column will be lost.
  - You are about to drop the column `started_at` on the `GameCivTechnology` table. All the data in the column will be lost.
  - You are about to drop the column `tech_id` on the `GameCivTechnology` table. All the data in the column will be lost.
  - You are about to drop the column `created_turn` on the `GameUnit` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `GameUnit` table. All the data in the column will be lost.
  - You are about to drop the column `promotion_level` on the `GameUnit` table. All the data in the column will be lost.
  - You are about to drop the column `unit_type_id` on the `GameUnit` table. All the data in the column will be lost.
  - You are about to drop the column `civ_type_id` on the `LeaderProfile` table. All the data in the column will be lost.
  - You are about to drop the column `created_at` on the `LeaderProfile` table. All the data in the column will be lost.
  - You are about to drop the column `full_name` on the `LeaderProfile` table. All the data in the column will be lost.
  - You are about to drop the column `image_url` on the `LeaderProfile` table. All the data in the column will be lost.
  - You are about to drop the column `preferred_victories` on the `LeaderProfile` table. All the data in the column will be lost.
  - You are about to drop the column `updated_at` on the `LeaderProfile` table. All the data in the column will be lost.
  - The primary key for the `MapTile` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the column `game_id` on the `MapTile` table. All the data in the column will be lost.
  - You are about to drop the column `building_id` on the `PlayerBuilding` table. All the data in the column will be lost.
  - You are about to drop the column `city_id` on the `PlayerBuilding` table. All the data in the column will be lost.
  - You are about to drop the column `completed_at` on the `PlayerBuilding` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `PlayerBuilding` table. All the data in the column will be lost.
  - You are about to drop the column `started_at` on the `PlayerBuilding` table. All the data in the column will be lost.
  - You are about to drop the column `prereq_id` on the `Prerequisite` table. All the data in the column will be lost.
  - You are about to drop the column `tech_id` on the `Prerequisite` table. All the data in the column will be lost.
  - You are about to drop the column `added_at` on the `ProductionQueue` table. All the data in the column will be lost.
  - You are about to drop the column `city_id` on the `ProductionQueue` table. All the data in the column will be lost.
  - You are about to drop the column `item_id` on the `ProductionQueue` table. All the data in the column will be lost.
  - You are about to drop the column `item_type` on the `ProductionQueue` table. All the data in the column will be lost.
  - You are about to drop the column `queue_order` on the `ProductionQueue` table. All the data in the column will be lost.
  - You are about to drop the column `turns_left` on the `ProductionQueue` table. All the data in the column will be lost.
  - You are about to drop the column `added_at` on the `ResearchQueue` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `ResearchQueue` table. All the data in the column will be lost.
  - You are about to drop the column `queue_position` on the `ResearchQueue` table. All the data in the column will be lost.
  - You are about to drop the column `tech_id` on the `ResearchQueue` table. All the data in the column will be lost.
  - You are about to drop the column `research_cost` on the `Technology` table. All the data in the column will be lost.
  - You are about to drop the column `research_time_modifier` on the `Technology` table. All the data in the column will be lost.
  - You are about to drop the column `tree_type` on the `Technology` table. All the data in the column will be lost.
  - You are about to drop the column `game_civ_id` on the `TreeSelection` table. All the data in the column will be lost.
  - You are about to drop the column `is_main` on the `TreeSelection` table. All the data in the column will be lost.
  - You are about to drop the column `selected_at` on the `TreeSelection` table. All the data in the column will be lost.
  - You are about to drop the column `tree_type` on the `TreeSelection` table. All the data in the column will be lost.
  - You are about to drop the column `civ_id` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `created_at` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `diplomacy_state` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `game_id` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `observed_map` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `production_state` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `research_state` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `turn_number` on the `TurnSnapshot` table. All the data in the column will be lost.
  - You are about to drop the column `build_time` on the `UnitType` table. All the data in the column will be lost.
  - You are about to drop the column `prereq_tech_id` on the `UnitType` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[civTypeId]` on the table `LeaderProfile` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `gameCivId` to the `AdviceRequest` table without a default value. This is not possible if the table is not empty.
  - Added the required column `usedCount` to the `AdviceRequest` table without a default value. This is not possible if the table is not empty.
  - Added the required column `buildingId` to the `BuildQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `cityId` to the `BuildQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `queuePosition` to the `BuildQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `buildTime` to the `Building` table without a default value. This is not possible if the table is not empty.
  - Added the required column `maintenanceCost` to the `Building` table without a default value. This is not possible if the table is not empty.
  - Added the required column `resourceCost` to the `Building` table without a default value. This is not possible if the table is not empty.
  - Added the required column `createdTurn` to the `City` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameCivId` to the `City` table without a default value. This is not possible if the table is not empty.
  - Added the required column `leaderName` to the `CivType` table without a default value. This is not possible if the table is not empty.
  - Added the required column `actionType` to the `DiplomacyAction` table without a default value. This is not possible if the table is not empty.
  - Added the required column `newScore` to the `DiplomacyAction` table without a default value. This is not possible if the table is not empty.
  - Added the required column `sessionId` to the `DiplomacyAction` table without a default value. This is not possible if the table is not empty.
  - Added the required column `aiCivId` to the `DiplomacySession` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameCivId` to the `DiplomacySession` table without a default value. This is not possible if the table is not empty.
  - Added the required column `relationshipScore` to the `DiplomacySession` table without a default value. This is not possible if the table is not empty.
  - Added the required column `sessionId` to the `DiplomacySession` table without a default value. This is not possible if the table is not empty.
  - Added the required column `mapRadius` to the `Game` table without a default value. This is not possible if the table is not empty.
  - Added the required column `turnLimit` to the `Game` table without a default value. This is not possible if the table is not empty.
  - Added the required column `userName` to the `Game` table without a default value. This is not possible if the table is not empty.
  - Added the required column `civTypeId` to the `GameCiv` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameId` to the `GameCiv` table without a default value. This is not possible if the table is not empty.
  - Added the required column `isPlayer` to the `GameCiv` table without a default value. This is not possible if the table is not empty.
  - Added the required column `startQ` to the `GameCiv` table without a default value. This is not possible if the table is not empty.
  - Added the required column `startR` to the `GameCiv` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameCivId` to the `GameCivTechnology` table without a default value. This is not possible if the table is not empty.
  - Added the required column `techId` to the `GameCivTechnology` table without a default value. This is not possible if the table is not empty.
  - Added the required column `createdTurn` to the `GameUnit` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameCivId` to the `GameUnit` table without a default value. This is not possible if the table is not empty.
  - Added the required column `unitTypeId` to the `GameUnit` table without a default value. This is not possible if the table is not empty.
  - Added the required column `civTypeId` to the `LeaderProfile` table without a default value. This is not possible if the table is not empty.
  - Added the required column `fullName` to the `LeaderProfile` table without a default value. This is not possible if the table is not empty.
  - Added the required column `updatedAt` to the `LeaderProfile` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameId` to the `MapTile` table without a default value. This is not possible if the table is not empty.
  - Added the required column `buildingId` to the `PlayerBuilding` table without a default value. This is not possible if the table is not empty.
  - Added the required column `cityId` to the `PlayerBuilding` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameCivId` to the `PlayerBuilding` table without a default value. This is not possible if the table is not empty.
  - Added the required column `prereqId` to the `Prerequisite` table without a default value. This is not possible if the table is not empty.
  - Added the required column `techId` to the `Prerequisite` table without a default value. This is not possible if the table is not empty.
  - Added the required column `cityId` to the `ProductionQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `itemId` to the `ProductionQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `itemType` to the `ProductionQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `queueOrder` to the `ProductionQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `turnsLeft` to the `ProductionQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameCivId` to the `ResearchQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `queuePosition` to the `ResearchQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `techId` to the `ResearchQueue` table without a default value. This is not possible if the table is not empty.
  - Added the required column `researchCost` to the `Technology` table without a default value. This is not possible if the table is not empty.
  - Added the required column `researchTimeModifier` to the `Technology` table without a default value. This is not possible if the table is not empty.
  - Added the required column `treeType` to the `Technology` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameCivId` to the `TreeSelection` table without a default value. This is not possible if the table is not empty.
  - Added the required column `isMain` to the `TreeSelection` table without a default value. This is not possible if the table is not empty.
  - Added the required column `treeType` to the `TreeSelection` table without a default value. This is not possible if the table is not empty.
  - Added the required column `civId` to the `TurnSnapshot` table without a default value. This is not possible if the table is not empty.
  - Added the required column `diplomacyState` to the `TurnSnapshot` table without a default value. This is not possible if the table is not empty.
  - Added the required column `gameId` to the `TurnSnapshot` table without a default value. This is not possible if the table is not empty.
  - Added the required column `observedMap` to the `TurnSnapshot` table without a default value. This is not possible if the table is not empty.
  - Added the required column `productionState` to the `TurnSnapshot` table without a default value. This is not possible if the table is not empty.
  - Added the required column `researchState` to the `TurnSnapshot` table without a default value. This is not possible if the table is not empty.
  - Added the required column `turnNumber` to the `TurnSnapshot` table without a default value. This is not possible if the table is not empty.
  - Added the required column `buildTime` to the `UnitType` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE `AdviceRequest` DROP FOREIGN KEY `AdviceRequest_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `BuildQueue` DROP FOREIGN KEY `BuildQueue_building_id_fkey`;

-- DropForeignKey
ALTER TABLE `Building` DROP FOREIGN KEY `Building_prerequisite_tech_id_fkey`;

-- DropForeignKey
ALTER TABLE `City` DROP FOREIGN KEY `City_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `DiplomacyAction` DROP FOREIGN KEY `DiplomacyAction_session_id_fkey`;

-- DropForeignKey
ALTER TABLE `DiplomacySession` DROP FOREIGN KEY `DiplomacySession_ai_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `DiplomacySession` DROP FOREIGN KEY `DiplomacySession_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `GameCiv` DROP FOREIGN KEY `GameCiv_civ_type_id_fkey`;

-- DropForeignKey
ALTER TABLE `GameCiv` DROP FOREIGN KEY `GameCiv_game_id_fkey`;

-- DropForeignKey
ALTER TABLE `GameCivTechnology` DROP FOREIGN KEY `GameCivTechnology_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `GameCivTechnology` DROP FOREIGN KEY `GameCivTechnology_tech_id_fkey`;

-- DropForeignKey
ALTER TABLE `GameUnit` DROP FOREIGN KEY `GameUnit_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `GameUnit` DROP FOREIGN KEY `GameUnit_unit_type_id_fkey`;

-- DropForeignKey
ALTER TABLE `LeaderProfile` DROP FOREIGN KEY `LeaderProfile_civ_type_id_fkey`;

-- DropForeignKey
ALTER TABLE `MapTile` DROP FOREIGN KEY `MapTile_game_id_fkey`;

-- DropForeignKey
ALTER TABLE `PlayerBuilding` DROP FOREIGN KEY `PlayerBuilding_building_id_fkey`;

-- DropForeignKey
ALTER TABLE `PlayerBuilding` DROP FOREIGN KEY `PlayerBuilding_city_id_fkey`;

-- DropForeignKey
ALTER TABLE `PlayerBuilding` DROP FOREIGN KEY `PlayerBuilding_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `Prerequisite` DROP FOREIGN KEY `Prerequisite_prereq_id_fkey`;

-- DropForeignKey
ALTER TABLE `Prerequisite` DROP FOREIGN KEY `Prerequisite_tech_id_fkey`;

-- DropForeignKey
ALTER TABLE `ProductionQueue` DROP FOREIGN KEY `ProductionQueue_city_id_fkey`;

-- DropForeignKey
ALTER TABLE `ResearchQueue` DROP FOREIGN KEY `ResearchQueue_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `ResearchQueue` DROP FOREIGN KEY `ResearchQueue_tech_id_fkey`;

-- DropForeignKey
ALTER TABLE `TreeSelection` DROP FOREIGN KEY `TreeSelection_game_civ_id_fkey`;

-- DropForeignKey
ALTER TABLE `TurnSnapshot` DROP FOREIGN KEY `TurnSnapshot_game_id_fkey`;

-- DropForeignKey
ALTER TABLE `UnitType` DROP FOREIGN KEY `UnitType_prereq_tech_id_fkey`;

-- AlterTable
ALTER TABLE `AdviceRequest` DROP COLUMN `created_at`,
    DROP COLUMN `game_civ_id`,
    DROP COLUMN `used_count`,
    ADD COLUMN `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `gameCivId` BIGINT NOT NULL,
    ADD COLUMN `usedCount` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `BuildQueue` DROP COLUMN `added_at`,
    DROP COLUMN `building_id`,
    DROP COLUMN `city_id`,
    DROP COLUMN `queue_position`,
    ADD COLUMN `addedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `buildingId` INTEGER NOT NULL,
    ADD COLUMN `cityId` BIGINT NOT NULL,
    ADD COLUMN `queuePosition` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `Building` DROP COLUMN `build_time`,
    DROP COLUMN `maintenance_cost`,
    DROP COLUMN `prerequisite_tech_id`,
    DROP COLUMN `resource_cost`,
    ADD COLUMN `buildTime` INTEGER NOT NULL,
    ADD COLUMN `maintenanceCost` INTEGER NOT NULL,
    ADD COLUMN `prerequisiteTechId` INTEGER NULL,
    ADD COLUMN `resourceCost` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `City` DROP COLUMN `created_turn`,
    DROP COLUMN `game_civ_id`,
    ADD COLUMN `createdTurn` INTEGER NOT NULL,
    ADD COLUMN `gameCivId` BIGINT NOT NULL;

-- AlterTable
ALTER TABLE `CivType` DROP COLUMN `leader_name`,
    ADD COLUMN `leaderName` VARCHAR(50) NOT NULL;

-- AlterTable
ALTER TABLE `DiplomacyAction` DROP COLUMN `action_type`,
    DROP COLUMN `new_score`,
    DROP COLUMN `session_id`,
    ADD COLUMN `actionType` ENUM('declare_friendship', 'propose_trade', 'declare_war', 'make_peace', 'offer_alliance') NOT NULL,
    ADD COLUMN `newScore` INTEGER NOT NULL,
    ADD COLUMN `sessionId` BIGINT NOT NULL;

-- AlterTable
ALTER TABLE `DiplomacySession` DROP PRIMARY KEY,
    DROP COLUMN `ai_civ_id`,
    DROP COLUMN `game_civ_id`,
    DROP COLUMN `relationship_score`,
    DROP COLUMN `session_id`,
    ADD COLUMN `aiCivId` BIGINT NOT NULL,
    ADD COLUMN `gameCivId` BIGINT NOT NULL,
    ADD COLUMN `relationshipScore` INTEGER NOT NULL,
    ADD COLUMN `sessionId` BIGINT NOT NULL AUTO_INCREMENT,
    ADD PRIMARY KEY (`sessionId`);

-- AlterTable
ALTER TABLE `Game` DROP COLUMN `created_at`,
    DROP COLUMN `map_radius`,
    DROP COLUMN `turn_limit`,
    DROP COLUMN `user_name`,
    ADD COLUMN `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `mapRadius` INTEGER NOT NULL,
    ADD COLUMN `turnLimit` INTEGER NOT NULL,
    ADD COLUMN `userName` VARCHAR(50) NOT NULL;

-- AlterTable
ALTER TABLE `GameCiv` DROP COLUMN `civ_type_id`,
    DROP COLUMN `game_id`,
    DROP COLUMN `is_player`,
    DROP COLUMN `start_q`,
    DROP COLUMN `start_r`,
    ADD COLUMN `civTypeId` INTEGER NOT NULL,
    ADD COLUMN `gameId` BIGINT NOT NULL,
    ADD COLUMN `isPlayer` BOOLEAN NOT NULL,
    ADD COLUMN `startQ` INTEGER NOT NULL,
    ADD COLUMN `startR` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `GameCivTechnology` DROP COLUMN `completed_at`,
    DROP COLUMN `game_civ_id`,
    DROP COLUMN `progress_points`,
    DROP COLUMN `started_at`,
    DROP COLUMN `tech_id`,
    ADD COLUMN `completedAt` DATETIME(3) NULL,
    ADD COLUMN `gameCivId` BIGINT NOT NULL,
    ADD COLUMN `progressPoints` INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN `startedAt` DATETIME(3) NULL,
    ADD COLUMN `techId` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `GameUnit` DROP COLUMN `created_turn`,
    DROP COLUMN `game_civ_id`,
    DROP COLUMN `promotion_level`,
    DROP COLUMN `unit_type_id`,
    ADD COLUMN `createdTurn` INTEGER NOT NULL,
    ADD COLUMN `gameCivId` BIGINT NOT NULL,
    ADD COLUMN `promotionLevel` INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN `unitTypeId` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `LeaderProfile` DROP COLUMN `civ_type_id`,
    DROP COLUMN `created_at`,
    DROP COLUMN `full_name`,
    DROP COLUMN `image_url`,
    DROP COLUMN `preferred_victories`,
    DROP COLUMN `updated_at`,
    ADD COLUMN `civTypeId` INTEGER NOT NULL,
    ADD COLUMN `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `fullName` VARCHAR(100) NOT NULL,
    ADD COLUMN `imageUrl` VARCHAR(255) NULL,
    ADD COLUMN `preferredVictories` VARCHAR(191) NULL,
    ADD COLUMN `updatedAt` DATETIME(3) NOT NULL,
    MODIFY `backstory` VARCHAR(191) NULL;

-- AlterTable
ALTER TABLE `MapTile` DROP PRIMARY KEY,
    DROP COLUMN `game_id`,
    ADD COLUMN `gameId` BIGINT NOT NULL,
    ADD PRIMARY KEY (`gameId`, `q`, `r`);

-- AlterTable
ALTER TABLE `PlayerBuilding` DROP COLUMN `building_id`,
    DROP COLUMN `city_id`,
    DROP COLUMN `completed_at`,
    DROP COLUMN `game_civ_id`,
    DROP COLUMN `started_at`,
    ADD COLUMN `buildingId` INTEGER NOT NULL,
    ADD COLUMN `cityId` BIGINT NOT NULL,
    ADD COLUMN `completedAt` DATETIME(3) NULL,
    ADD COLUMN `gameCivId` BIGINT NOT NULL,
    ADD COLUMN `startedAt` DATETIME(3) NULL;

-- AlterTable
ALTER TABLE `Prerequisite` DROP COLUMN `prereq_id`,
    DROP COLUMN `tech_id`,
    ADD COLUMN `prereqId` INTEGER NOT NULL,
    ADD COLUMN `techId` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `ProductionQueue` DROP COLUMN `added_at`,
    DROP COLUMN `city_id`,
    DROP COLUMN `item_id`,
    DROP COLUMN `item_type`,
    DROP COLUMN `queue_order`,
    DROP COLUMN `turns_left`,
    ADD COLUMN `addedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `cityId` BIGINT NOT NULL,
    ADD COLUMN `itemId` INTEGER NOT NULL,
    ADD COLUMN `itemType` ENUM('unit', 'building') NOT NULL,
    ADD COLUMN `queueOrder` INTEGER NOT NULL,
    ADD COLUMN `turnsLeft` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `ResearchQueue` DROP COLUMN `added_at`,
    DROP COLUMN `game_civ_id`,
    DROP COLUMN `queue_position`,
    DROP COLUMN `tech_id`,
    ADD COLUMN `addedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `gameCivId` BIGINT NOT NULL,
    ADD COLUMN `queuePosition` INTEGER NOT NULL,
    ADD COLUMN `techId` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `Technology` DROP COLUMN `research_cost`,
    DROP COLUMN `research_time_modifier`,
    DROP COLUMN `tree_type`,
    ADD COLUMN `researchCost` INTEGER NOT NULL,
    ADD COLUMN `researchTimeModifier` DOUBLE NOT NULL,
    ADD COLUMN `treeType` VARCHAR(50) NOT NULL;

-- AlterTable
ALTER TABLE `TreeSelection` DROP COLUMN `game_civ_id`,
    DROP COLUMN `is_main`,
    DROP COLUMN `selected_at`,
    DROP COLUMN `tree_type`,
    ADD COLUMN `gameCivId` BIGINT NOT NULL,
    ADD COLUMN `isMain` BOOLEAN NOT NULL,
    ADD COLUMN `selectedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `treeType` VARCHAR(50) NOT NULL;

-- AlterTable
ALTER TABLE `TurnSnapshot` DROP COLUMN `civ_id`,
    DROP COLUMN `created_at`,
    DROP COLUMN `diplomacy_state`,
    DROP COLUMN `game_id`,
    DROP COLUMN `observed_map`,
    DROP COLUMN `production_state`,
    DROP COLUMN `research_state`,
    DROP COLUMN `turn_number`,
    ADD COLUMN `civId` BIGINT NOT NULL,
    ADD COLUMN `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ADD COLUMN `diplomacyState` JSON NOT NULL,
    ADD COLUMN `gameId` BIGINT NOT NULL,
    ADD COLUMN `observedMap` JSON NOT NULL,
    ADD COLUMN `productionState` JSON NOT NULL,
    ADD COLUMN `researchState` JSON NOT NULL,
    ADD COLUMN `turnNumber` INTEGER NOT NULL;

-- AlterTable
ALTER TABLE `UnitType` DROP COLUMN `build_time`,
    DROP COLUMN `prereq_tech_id`,
    ADD COLUMN `buildTime` INTEGER NOT NULL,
    ADD COLUMN `prereqTechId` INTEGER NULL;

-- CreateIndex
CREATE UNIQUE INDEX `LeaderProfile_civTypeId_key` ON `LeaderProfile`(`civTypeId`);

-- AddForeignKey
ALTER TABLE `GameCiv` ADD CONSTRAINT `GameCiv_gameId_fkey` FOREIGN KEY (`gameId`) REFERENCES `Game`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameCiv` ADD CONSTRAINT `GameCiv_civTypeId_fkey` FOREIGN KEY (`civTypeId`) REFERENCES `CivType`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `MapTile` ADD CONSTRAINT `MapTile_gameId_fkey` FOREIGN KEY (`gameId`) REFERENCES `Game`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `City` ADD CONSTRAINT `City_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Prerequisite` ADD CONSTRAINT `Prerequisite_techId_fkey` FOREIGN KEY (`techId`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Prerequisite` ADD CONSTRAINT `Prerequisite_prereqId_fkey` FOREIGN KEY (`prereqId`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameCivTechnology` ADD CONSTRAINT `GameCivTechnology_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameCivTechnology` ADD CONSTRAINT `GameCivTechnology_techId_fkey` FOREIGN KEY (`techId`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `TreeSelection` ADD CONSTRAINT `TreeSelection_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ResearchQueue` ADD CONSTRAINT `ResearchQueue_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ResearchQueue` ADD CONSTRAINT `ResearchQueue_techId_fkey` FOREIGN KEY (`techId`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `UnitType` ADD CONSTRAINT `UnitType_prereqTechId_fkey` FOREIGN KEY (`prereqTechId`) REFERENCES `Technology`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameUnit` ADD CONSTRAINT `GameUnit_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameUnit` ADD CONSTRAINT `GameUnit_unitTypeId_fkey` FOREIGN KEY (`unitTypeId`) REFERENCES `UnitType`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ProductionQueue` ADD CONSTRAINT `ProductionQueue_cityId_fkey` FOREIGN KEY (`cityId`) REFERENCES `City`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Building` ADD CONSTRAINT `Building_prerequisiteTechId_fkey` FOREIGN KEY (`prerequisiteTechId`) REFERENCES `Technology`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `PlayerBuilding` ADD CONSTRAINT `PlayerBuilding_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `PlayerBuilding` ADD CONSTRAINT `PlayerBuilding_cityId_fkey` FOREIGN KEY (`cityId`) REFERENCES `City`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `PlayerBuilding` ADD CONSTRAINT `PlayerBuilding_buildingId_fkey` FOREIGN KEY (`buildingId`) REFERENCES `Building`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `BuildQueue` ADD CONSTRAINT `BuildQueue_buildingId_fkey` FOREIGN KEY (`buildingId`) REFERENCES `Building`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `DiplomacySession` ADD CONSTRAINT `DiplomacySession_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `DiplomacySession` ADD CONSTRAINT `DiplomacySession_aiCivId_fkey` FOREIGN KEY (`aiCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `DiplomacyAction` ADD CONSTRAINT `DiplomacyAction_sessionId_fkey` FOREIGN KEY (`sessionId`) REFERENCES `DiplomacySession`(`sessionId`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `AdviceRequest` ADD CONSTRAINT `AdviceRequest_gameCivId_fkey` FOREIGN KEY (`gameCivId`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `TurnSnapshot` ADD CONSTRAINT `TurnSnapshot_gameId_fkey` FOREIGN KEY (`gameId`) REFERENCES `Game`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `LeaderProfile` ADD CONSTRAINT `LeaderProfile_civTypeId_fkey` FOREIGN KEY (`civTypeId`) REFERENCES `CivType`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
