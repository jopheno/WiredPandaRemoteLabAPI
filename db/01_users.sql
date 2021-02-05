CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `login` varchar(32) NOT NULL,
  `password` char(64) NOT NULL,
  `last_logged_in` int(11) unsigned NOT NULL DEFAULT '0',
  `email` varchar(255) NOT NULL,
  `created` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `login` (`login`)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8;

-- INSERTs

INSERT INTO `users` (`login`, `password`, `last_logged_in`, `email`, `created`)
VALUES ('admin', '21232f297a57a5a743894a0e4a801fc3', 1577836800, 'admin@mail.com', 315532800);

INSERT INTO `users` (`login`, `password`, `last_logged_in`, `email`, `created`)
VALUES ('test', '098f6bcd4621d373cade4e832627b4f6', 1577901600, 'test@mail.com', 315532800);
