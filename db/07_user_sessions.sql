CREATE TABLE IF NOT EXISTS `user_sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `secret` char(16) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

ALTER TABLE `user_sessions` ADD FOREIGN KEY (`user_id`) REFERENCES `users`(`id`);

-- INSERTs
