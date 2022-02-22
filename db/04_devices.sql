CREATE TABLE IF NOT EXISTS `devices` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` int(11) NOT NULL,
  `method` int(11) NOT NULL,
  `being_used_by` int(11) DEFAULT NULL,
  `session` char(16) DEFAULT NULL,
  `token` char(12) DEFAULT NULL,
  `serial_port` char(22) DEFAULT NULL,
  `using_since` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

ALTER TABLE `devices` ADD FOREIGN KEY (`type`) REFERENCES `device_types`(`id`);
ALTER TABLE `devices` ADD FOREIGN KEY (`method`) REFERENCES `device_methods`(`id`);

-- INSERTs

INSERT INTO `devices` (`type`, `method`, `being_used_by`, `session`, `token`, `serial_port`)
VALUES (1, 1, NULL, NULL, '', '/dev/ttyUSB0');
