#!/usr/bin/env bash
sudo /etc/init.d/lircd stop
sudo cp /home/pi/$1.lircd.conf /etc/lirc/lircd.conf
sudo /etc/init.d/lircd restart
irsend SEND_ONCE $1 $2
