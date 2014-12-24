#!/bin/bash

if ! [ `which ansible` ]; then
    sudo yum install -y ansible bind-utils telnet httpd-tools http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
fi

PATH=/var/www/app/bin:/usr/local/bin:/usr/pgsql-9.3/bin:$PATH LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 PYTHONUNBUFFERED=1 ansible-playbook --connection=local /vagrant/ansible/vagrant.yml
