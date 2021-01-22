CREATE TABLE IF NOT EXISTS `device_type_methods` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` int(11) NOT NULL,
  `name` char(40) DEFAULT NULL,
  `latency` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

ALTER TABLE `device_type_methods` ADD FOREIGN KEY (`type`) REFERENCES `device_types`(`id`);

-- INSERTs

INSERT INTO `device_type_methods` (`type`, `name`, `latency`)
VALUES (1, 'VirtualHere', 80);
