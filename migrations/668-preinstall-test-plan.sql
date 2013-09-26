CREATE TABLE `preinstall_test_plan` (
    `id` int(11) unsigned NOT NULL auto_increment,
    `addon_id` int(11) unsigned NOT NULL,
    `created` datetime NOT NULL,
    `modified` datetime NOT NULL,
    `last_submission` datetime NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

ALTER TABLE `preinstall_test_plan` ADD CONSTRAINT `preinstall_test_plan_addon_fk` FOREIGN KEY (`addon_id`) REFERENCES `addons` (`id`);
