-- MySQL dump 10.13  Distrib 8.0.34, for Linux (x86_64)
--
-- Host: localhost    Database: Aiogram2
-- ------------------------------------------------------
-- Server version	8.0.34-0ubuntu0.20.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `bot_groups`
--

DROP TABLE IF EXISTS `bot_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bot_groups` (
  `id` bigint NOT NULL,
  `title` varchar(100) DEFAULT NULL,
  `owner_id` bigint NOT NULL,
  `type` varchar(50) DEFAULT NULL,
  `add_date` varchar(200) DEFAULT NULL,
  KEY `owner_id` (`owner_id`),
  KEY `group_id` (`id`),
  CONSTRAINT `bot_groups_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bot_groups`
--

LOCK TABLES `bot_groups` WRITE;
/*!40000 ALTER TABLE `bot_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `bot_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tic_tac_toe_game`
--

DROP TABLE IF EXISTS `tic_tac_toe_game`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tic_tac_toe_game` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` bigint DEFAULT NULL,
  `user_start_message_id` bigint DEFAULT NULL,
  `last_ready_message_id` bigint DEFAULT NULL,
  `main_game_message_id` bigint DEFAULT NULL,
  `fighter1_username` varchar(100) DEFAULT NULL,
  `fighter1_id` bigint DEFAULT NULL,
  `fighter1_ready` tinyint(1) DEFAULT NULL,
  `fighter2_username` varchar(100) DEFAULT NULL,
  `fighter2_id` bigint DEFAULT NULL,
  `fighter2_ready` tinyint(1) DEFAULT NULL,
  `ended` tinyint(1) DEFAULT NULL,
  `winner_username` varchar(100) DEFAULT NULL,
  `winner_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `group_id` (`group_id`),
  CONSTRAINT `tic_tac_toe_game_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `bot_groups` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=259 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tic_tac_toe_game`
--

LOCK TABLES `tic_tac_toe_game` WRITE;
/*!40000 ALTER TABLE `tic_tac_toe_game` DISABLE KEYS */;
/*!40000 ALTER TABLE `tic_tac_toe_game` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tic_tac_toe_temp`
--

DROP TABLE IF EXISTS `tic_tac_toe_temp`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tic_tac_toe_temp` (
  `id` int NOT NULL AUTO_INCREMENT,
  `game_id` int NOT NULL,
  `current_picker_id` bigint NOT NULL,
  `current_filler` varchar(10) DEFAULT NULL,
  `map_positions` varchar(200) DEFAULT NULL,
  `fillers` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `game_id` (`game_id`),
  CONSTRAINT `tic_tac_toe_temp_ibfk_1` FOREIGN KEY (`game_id`) REFERENCES `tic_tac_toe_game` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=86 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tic_tac_toe_temp`
--

LOCK TABLES `tic_tac_toe_temp` WRITE;
/*!40000 ALTER TABLE `tic_tac_toe_temp` DISABLE KEYS */;
/*!40000 ALTER TABLE `tic_tac_toe_temp` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint NOT NULL,
  `username` varchar(100) DEFAULT NULL,
  `date_registration` varchar(200) DEFAULT NULL,
  `has_active_groups` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users_groups_actions`
--

DROP TABLE IF EXISTS `users_groups_actions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_groups_actions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `group_id` (`group_id`),
  CONSTRAINT `users_groups_actions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `users_groups_actions_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `bot_groups` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_groups_actions`
--

LOCK TABLES `users_groups_actions` WRITE;
/*!40000 ALTER TABLE `users_groups_actions` DISABLE KEYS */;
/*!40000 ALTER TABLE `users_groups_actions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users_groups_settings`
--

DROP TABLE IF EXISTS `users_groups_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_groups_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` bigint NOT NULL,
  `owner_id` bigint NOT NULL,
  `use_notify_for_ban_user` tinyint(1) DEFAULT NULL,
  `use_notify_for_unban_user` tinyint(1) DEFAULT NULL,
  `use_banwords_filter` tinyint(1) DEFAULT NULL,
  `banwords_list` mediumtext,
  `muted_users_list` mediumtext,
  PRIMARY KEY (`id`),
  KEY `group_id` (`group_id`),
  KEY `owner_id` (`owner_id`),
  CONSTRAINT `users_groups_settings_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `bot_groups` (`id`) ON DELETE CASCADE,
  CONSTRAINT `users_groups_settings_ibfk_2` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=72 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_groups_settings`
--

LOCK TABLES `users_groups_settings` WRITE;
/*!40000 ALTER TABLE `users_groups_settings` DISABLE KEYS */;
/*!40000 ALTER TABLE `users_groups_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users_moderations`
--

DROP TABLE IF EXISTS `users_moderations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_moderations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` bigint NOT NULL,
  `warn_message_id` int DEFAULT NULL,
  `question_message_id` bigint DEFAULT NULL,
  `from_user` bigint NOT NULL,
  `to_user` bigint NOT NULL,
  `to_user_full_name` varchar(100) DEFAULT NULL,
  `action` varchar(50) DEFAULT NULL,
  `ban_days` int DEFAULT NULL,
  `ended` tinyint(1) DEFAULT NULL,
  `from_bot` tinyint(1) DEFAULT NULL,
  `to_bot` tinyint(1) DEFAULT NULL,
  `date` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `group_id` (`group_id`),
  KEY `warn_message_id_index` (`warn_message_id`) USING BTREE,
  KEY `from_user_index` (`from_user`) USING BTREE,
  KEY `to_user_index` (`to_user`) USING BTREE,
  CONSTRAINT `users_moderations_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `bot_groups` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=179 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_moderations`
--

LOCK TABLES `users_moderations` WRITE;
/*!40000 ALTER TABLE `users_moderations` DISABLE KEYS */;
/*!40000 ALTER TABLE `users_moderations` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-10-30  0:01:43
