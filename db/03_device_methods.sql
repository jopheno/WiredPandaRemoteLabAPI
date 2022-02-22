CREATE TABLE IF NOT EXISTS `device_methods` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` char(40) DEFAULT NULL,
  `latency` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

ALTER TABLE `device_methods` ADD FOREIGN KEY (`type`) REFERENCES `device_types`(`id`);

-- INSERTs

INSERT INTO `device_methods` (`name`, `latency`)
VALUES ('VirtualHere', 80);
