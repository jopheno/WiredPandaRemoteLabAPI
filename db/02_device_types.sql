CREATE TABLE IF NOT EXISTS `device_types` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) NOT NULL,
  `description` char(40) NOT NULL,
  `allowed_time` int(11) NOT NULL DEFAULT '600',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

-- INSERTs

INSERT INTO `device_types` (`name`, `description`, `allowed_time`)
VALUES ('DE2-115', 'Kit DE2-115 com 55 portas disponíveis', 45);
