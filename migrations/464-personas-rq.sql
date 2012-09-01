CREATE TABLE `persona_locks` (
    `id` int(11) unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `persona_id` int(11) unsigned NOT NULL UNIQUE,
    `persona_lock_id` int(11) unsigned  NOT NULL,
    `reviewer_id` int(11) unsigned NOT NULL,
    `expiry` datetime NOT NULL
) ENGINE=InnoDB CHARACTER SET utf8 COLLATE utf8_general_ci;

ALTER TABLE `persona_locks` ADD CONSTRAINT `reviewer_id_refs_id_6928eea4` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`);
ALTER TABLE `persona_locks` ADD CONSTRAINT `persona_id_refs_id_3202bbda` FOREIGN KEY (`persona_id`) REFERENCES `personas` (`id`);

CREATE INDEX `persona_locks_12a931ea` ON `persona_locks` (`persona_lock_id`);
CREATE INDEX `persona_locks_d0f17e2b` ON `persona_locks` (`reviewer_id`);

