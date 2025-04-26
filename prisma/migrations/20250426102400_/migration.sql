-- CreateTable
CREATE TABLE `Game` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `map_radius` INTEGER NOT NULL,
    `turn_limit` INTEGER NOT NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `CivType` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `leader_name` VARCHAR(50) NOT NULL,
    `personality` ENUM('Diplomat', 'Warlike', 'Pacifist', 'Trader') NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `GameCiv` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_id` BIGINT NOT NULL,
    `civ_type_id` INTEGER NOT NULL,
    `is_player` BOOLEAN NOT NULL,
    `start_q` INTEGER NOT NULL,
    `start_r` INTEGER NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `MapTile` (
    `game_id` BIGINT NOT NULL,
    `q` INTEGER NOT NULL,
    `r` INTEGER NOT NULL,
    `terrain` VARCHAR(20) NOT NULL,
    `resource` ENUM('NoResource', 'Food', 'Production', 'Gold', 'Science') NOT NULL,

    PRIMARY KEY (`game_id`, `q`, `r`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `City` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `name` VARCHAR(50) NOT NULL,
    `q` INTEGER NOT NULL,
    `r` INTEGER NOT NULL,
    `population` INTEGER NOT NULL,
    `created_turn` INTEGER NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Technology` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `description` TEXT NOT NULL,
    `era` ENUM('Medieval', 'Industrial', 'Modern') NOT NULL,
    `tree_type` VARCHAR(50) NOT NULL,
    `research_cost` INTEGER NOT NULL,
    `research_time_modifier` DOUBLE NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Prerequisite` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `tech_id` INTEGER NOT NULL,
    `prereq_id` INTEGER NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `GameCivTechnology` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `tech_id` INTEGER NOT NULL,
    `status` ENUM('locked', 'available', 'in_progress', 'completed') NOT NULL,
    `progress_points` INTEGER NOT NULL DEFAULT 0,
    `started_at` DATETIME(3) NULL,
    `completed_at` DATETIME(3) NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `TreeSelection` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `tree_type` VARCHAR(50) NOT NULL,
    `is_main` BOOLEAN NOT NULL,
    `selected_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `ResearchQueue` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `tech_id` INTEGER NOT NULL,
    `queue_position` INTEGER NOT NULL,
    `added_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `UnitType` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `category` ENUM('Melee', 'Ranged', 'Cavalry', 'Siege', 'Modern') NOT NULL,
    `era` ENUM('Medieval', 'Industrial', 'Modern') NOT NULL,
    `build_time` INTEGER NOT NULL,
    `maintenance` INTEGER NOT NULL,
    `movement` INTEGER NOT NULL,
    `sight` INTEGER NOT NULL,
    `prereq_tech_id` INTEGER NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `GameUnit` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `unit_type_id` INTEGER NOT NULL,
    `q` INTEGER NOT NULL,
    `r` INTEGER NOT NULL,
    `hp` INTEGER NOT NULL,
    `moved` BOOLEAN NOT NULL DEFAULT false,
    `promotion_level` INTEGER NOT NULL DEFAULT 0,
    `created_turn` INTEGER NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `ProductionQueue` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `city_id` BIGINT NOT NULL,
    `queue_order` INTEGER NOT NULL,
    `item_type` ENUM('unit', 'building') NOT NULL,
    `item_id` INTEGER NOT NULL,
    `turns_left` INTEGER NOT NULL,
    `added_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Building` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `description` TEXT NOT NULL,
    `build_time` INTEGER NOT NULL,
    `resource_cost` INTEGER NOT NULL,
    `maintenance_cost` INTEGER NOT NULL,
    `prerequisite_tech_id` INTEGER NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `PlayerBuilding` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `city_id` BIGINT NOT NULL,
    `building_id` INTEGER NOT NULL,
    `status` ENUM('queued', 'in_progress', 'completed') NOT NULL,
    `started_at` DATETIME(3) NULL,
    `completed_at` DATETIME(3) NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `BuildQueue` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `city_id` BIGINT NOT NULL,
    `building_id` INTEGER NOT NULL,
    `queue_position` INTEGER NOT NULL,
    `added_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `DiplomacySession` (
    `session_id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `ai_civ_id` BIGINT NOT NULL,
    `relationship_score` INTEGER NOT NULL,
    `personality` ENUM('Diplomat', 'Warlike', 'Pacifist', 'Trader') NOT NULL,

    PRIMARY KEY (`session_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `DiplomacyAction` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `session_id` BIGINT NOT NULL,
    `turn` INTEGER NOT NULL,
    `action_type` ENUM('declare_friendship', 'propose_trade', 'declare_war', 'make_peace', 'offer_alliance') NOT NULL,
    `terms` JSON NOT NULL,
    `delta` INTEGER NOT NULL,
    `new_score` INTEGER NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `AdviceRequest` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_civ_id` BIGINT NOT NULL,
    `turn` INTEGER NOT NULL,
    `used_count` INTEGER NOT NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `TurnSnapshot` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `game_id` BIGINT NOT NULL,
    `turn_number` INTEGER NOT NULL,
    `civ_id` BIGINT NOT NULL,
    `observed_map` JSON NOT NULL,
    `research_state` JSON NOT NULL,
    `production_state` JSON NOT NULL,
    `diplomacy_state` JSON NOT NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `LeaderProfile` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `civ_type_id` INTEGER NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `backstory` TEXT NULL,
    `personality` ENUM('Diplomat', 'Warlike', 'Pacifist', 'Trader') NOT NULL,
    `preferred_victories` VARCHAR(191) NULL,
    `image_url` VARCHAR(255) NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updated_at` DATETIME(3) NOT NULL,

    UNIQUE INDEX `LeaderProfile_civ_type_id_key`(`civ_type_id`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `GameCiv` ADD CONSTRAINT `GameCiv_game_id_fkey` FOREIGN KEY (`game_id`) REFERENCES `Game`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameCiv` ADD CONSTRAINT `GameCiv_civ_type_id_fkey` FOREIGN KEY (`civ_type_id`) REFERENCES `CivType`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `MapTile` ADD CONSTRAINT `MapTile_game_id_fkey` FOREIGN KEY (`game_id`) REFERENCES `Game`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `City` ADD CONSTRAINT `City_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Prerequisite` ADD CONSTRAINT `Prerequisite_tech_id_fkey` FOREIGN KEY (`tech_id`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Prerequisite` ADD CONSTRAINT `Prerequisite_prereq_id_fkey` FOREIGN KEY (`prereq_id`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameCivTechnology` ADD CONSTRAINT `GameCivTechnology_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameCivTechnology` ADD CONSTRAINT `GameCivTechnology_tech_id_fkey` FOREIGN KEY (`tech_id`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `TreeSelection` ADD CONSTRAINT `TreeSelection_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ResearchQueue` ADD CONSTRAINT `ResearchQueue_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ResearchQueue` ADD CONSTRAINT `ResearchQueue_tech_id_fkey` FOREIGN KEY (`tech_id`) REFERENCES `Technology`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `UnitType` ADD CONSTRAINT `UnitType_prereq_tech_id_fkey` FOREIGN KEY (`prereq_tech_id`) REFERENCES `Technology`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameUnit` ADD CONSTRAINT `GameUnit_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `GameUnit` ADD CONSTRAINT `GameUnit_unit_type_id_fkey` FOREIGN KEY (`unit_type_id`) REFERENCES `UnitType`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ProductionQueue` ADD CONSTRAINT `ProductionQueue_city_id_fkey` FOREIGN KEY (`city_id`) REFERENCES `City`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Building` ADD CONSTRAINT `Building_prerequisite_tech_id_fkey` FOREIGN KEY (`prerequisite_tech_id`) REFERENCES `Technology`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `PlayerBuilding` ADD CONSTRAINT `PlayerBuilding_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `PlayerBuilding` ADD CONSTRAINT `PlayerBuilding_city_id_fkey` FOREIGN KEY (`city_id`) REFERENCES `City`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `PlayerBuilding` ADD CONSTRAINT `PlayerBuilding_building_id_fkey` FOREIGN KEY (`building_id`) REFERENCES `Building`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `BuildQueue` ADD CONSTRAINT `BuildQueue_building_id_fkey` FOREIGN KEY (`building_id`) REFERENCES `Building`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `DiplomacySession` ADD CONSTRAINT `DiplomacySession_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `DiplomacySession` ADD CONSTRAINT `DiplomacySession_ai_civ_id_fkey` FOREIGN KEY (`ai_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `DiplomacyAction` ADD CONSTRAINT `DiplomacyAction_session_id_fkey` FOREIGN KEY (`session_id`) REFERENCES `DiplomacySession`(`session_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `AdviceRequest` ADD CONSTRAINT `AdviceRequest_game_civ_id_fkey` FOREIGN KEY (`game_civ_id`) REFERENCES `GameCiv`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `TurnSnapshot` ADD CONSTRAINT `TurnSnapshot_game_id_fkey` FOREIGN KEY (`game_id`) REFERENCES `Game`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `LeaderProfile` ADD CONSTRAINT `LeaderProfile_civ_type_id_fkey` FOREIGN KEY (`civ_type_id`) REFERENCES `CivType`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
