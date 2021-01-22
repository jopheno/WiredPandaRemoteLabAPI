CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `login` varchar(32) NOT NULL,
  `password` char(64) NOT NULL,
  `secret` char(16) DEFAULT NULL,
  `last_logged_in` int(11) unsigned NOT NULL DEFAULT '0',
  `email` varchar(255) NOT NULL,
  `created` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `login` (`login`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

-- INSERTs

INSERT INTO `users` (`login`, `password`, `secret`, `last_logged_in`, `email`, `created`)
VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', NULL, 1577836800, 'admin@mail.com', 315532800);

INSERT INTO `users` (`login`, `password`, `secret`, `last_logged_in`, `email`, `created`)
VALUES ('test', '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08', NULL, 1577901600, 'test@mail.com', 315532800);
