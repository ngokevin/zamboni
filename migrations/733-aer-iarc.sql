ALTER TABLE `addons_excluded_regions`
    ADD COLUMN `is_iarc_excluded` bool NOT NULL DEFAULT false,
    DROP INDEX `addon_id`,
    ADD UNIQUE index(`addon_id`, `region`, `is_iarc_excluded`);
