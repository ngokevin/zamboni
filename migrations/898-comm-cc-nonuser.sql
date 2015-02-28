ALTER TABLE `comm_thread_cc`
    MODIFY COLUMN `user_id` int(11) unsigned NULL,
    ADD COLUMN `nonuser_email` varchar(255) NULL;
