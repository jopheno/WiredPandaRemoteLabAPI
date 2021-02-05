CREATE TABLE IF NOT EXISTS `device_type_queue` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` int(11) NOT NULL,
  `method_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `session` char(16) NOT NULL,
  `position` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

ALTER TABLE `device_type_queue` ADD FOREIGN KEY (`type`) REFERENCES `device_types`(`id`);
ALTER TABLE `device_type_queue` ADD FOREIGN KEY (`method_id`) REFERENCES `device_type_methods`(`id`);
ALTER TABLE `device_type_queue` ADD FOREIGN KEY (`user_id`) REFERENCES `users`(`id`);

-- INSERTs
