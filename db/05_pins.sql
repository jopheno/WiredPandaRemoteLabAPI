CREATE TABLE IF NOT EXISTS `device_pins` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `device` int(11) NOT NULL,
  `port` char(22) NOT NULL,
  `type` int(1) NOT NULL,
  `forward_from` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

ALTER TABLE `device_pins` ADD FOREIGN KEY (`device`) REFERENCES `devices`(`id`);

-- INSERTs

-- GPIO[0]
INSERT INTO `device_pins` (`id`, `device`, `port`, `type`, `forward_from`)
VALUES (1, 1, 'PIN_AB22', 3, 22);

-- GPIO[1]
INSERT INTO `device_pins` (`id`, `device`, `port`, `type`, `forward_from`)
VALUES (2, 1, 'PIN_AC15', 3, 23);

-- GPIO[2]
INSERT INTO `device_pins` (`id`, `device`, `port`, `type`, `forward_from`)
VALUES (3, 1, 'PIN_AB21', 3, 24);

-- GPIO[3]
INSERT INTO `device_pins` (`id`, `device`, `port`, `type`, `forward_from`)
VALUES (4, 1, 'PIN_Y17', 3, 25);

-- GPIO[4]
INSERT INTO `device_pins` (`id`, `device`, `port`, `type`, `forward_from`)
VALUES (5, 1, 'PIN_AC21', 3, 26);
