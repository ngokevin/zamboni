CREATE TABLE `personas_locked` (
    `id` int(11) unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `persona_locked_id` int(11) unsigned NOT NULL,
    `persona_id` int(11) unsigned NOT NULL UNIQUE,
    `reviewer_id` int(11) unsigned NOT NULL,
    `expiry` datetime NOT NULL
) ENGINE=InnoDB CHARACTER SET utf8 COLLATE utf8_general_ci;
;
ALTER TABLE `personas_locked` ADD CONSTRAINT `persona_id_refs_id_8fa999b3` FOREIGN KEY (`persona_id`) REFERENCES `personas` (`id`);
ALTER TABLE `personas_locked` ADD CONSTRAINT `reviewer_id_refs_id_b2478ae3` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`);
CREATE INDEX `personas_locked_94969f95` ON `personas_locked` (`persona_locked_id`);
CREATE INDEX `personas_locked_d0f17e2b` ON `personas_locked` (`reviewer_id`);
