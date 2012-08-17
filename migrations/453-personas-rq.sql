CREATE TABLE `persona_locks` (
    `id` int(11) unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `persona_lock_id` int(11) unsigned NOT NULL,
    `persona_id` int(11) unsigned NOT NULL UNIQUE,
    `reviewer_id` int(11) unsigned NOT NULL,
    `expiry` datetime NOT NULL
) ENGINE=InnoDB CHARACTER SET utf8 COLLATE utf8_general_ci;
;
ALTER TABLE `persona_locks` ADD CONSTRAINT `persona_id_refs_id_8fa999b3` FOREIGN KEY (`persona_id`) REFERENCES `personas` (`id`);
ALTER TABLE `persona_locks` ADD CONSTRAINT `reviewer_id_refs_id_b2478ae3` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`);
CREATE INDEX `persona_locks_94969f95` ON `personas_lock` (`persona_lock_id`);
CREATE INDEX `persona_locks_d0f17e2b` ON `personas_lock` (`reviewer_id`);
