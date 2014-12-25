from fabfile_base import *

def _env():
    'env'
    env.user = 'vagrant'
    env.app_name = 'app'
    env.base_dir = '/var/www/%s' % env.app_name
    env.git_clone = 'git@bitbucket.org:hoge/hoge'
    env.branch_option = ''
    env.pip_file = 'requirements.txt'
    update_dirs()

def localhost():
    'env'
    _env()
    env.hosts = ['localhost']
    env.password = 'vagrant'
    env.local = True
    update_dirs()
