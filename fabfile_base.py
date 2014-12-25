'''
base file
    https://gist.github.com/cyberdelia/354506
'''

import datetime
import pytz
import sys

from fabric.api import env, run, sudo, local, put, cd, execute
from fabric import operations
from fabric import colors

def version():
    'print the date of last deploy'
    _releases()
    print env.current_revision,
    with cd('%(current_path)s/%(app_name)s' % env):
        print run('git rev-parse --abbrev-ref HEAD', quiet=True)

def update_dirs():
    env.venv_dir = env.base_dir
    env.domain_path = env.base_dir
    env.current_path = env.base_dir + '/current'
    env.releases_path = env.base_dir + '/releases'
    env.shared_path = env.base_dir + '/shared'
    env.activate = 'source %(venv_dir)s/bin/activate' % env
    
def _releases():
    """List a releases made"""
    env.releases = sorted(run('ls -x %(releases_path)s' % env, quiet=True).split())
    if len(env.releases) >= 1:
        env.current_revision = env.releases[-1]
        env.current_release = '%(releases_path)s/%(current_revision)s' % env
    if len(env.releases) > 1:
        env.previous_revision = env.releases[-2]
        env.previous_release = '%(releases_path)s/%(previous_revision)s' % env

def enable(country_code):
    """maintenance off"""
    env['country_code'] = country_code
    run('rm %(shared_path)s/maintenance-%(country_code)s' % env, quiet=True)

def disable(country_code):
    """maintenance on"""
    env['country_code'] = country_code
    run('touch %(shared_path)s/maintenance-%(country_code)s' % env, quiet=True)

def restart():
    """Restarts your application"""
    print 'Reloading:',
    sys.stdout.flush()
    if env.get('local'):
        return _print_result(sudo('/etc/init.d/supervisord restart', quiet=True))

    r = []
    r.append(run('cat /tmp/uwsgi-master.pid | xargs kill -HUP' % env, quiet=True))
    r.append(sudo('/usr/bin/supervisorctl restart celery', quiet=True))
    _print_result(r)
        
def _permissions():
    """Make the release group-writable"""
    return

    sudo('chmod -R g+w %(domain_path)s' % { 'domain_path':env.domain_path })
    sudo('chown -R www-data:www-data %(domain_path)s' % { 'domain_path':env.domain_path })

def setup():
    """Prepares one or more servers for deployment"""
    run('mkdir -p %(base_dir)s/releases' % env, quiet=True)
    run('mkdir -p %(shared_path)s/{datastore,media,node_modules,bower_components}' % env, quiet=True)
    _permissions()

def _checkout():
    """Checkout code to the remote servers"""
    from time import time
    env.time = time()

    import datetime
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.datetime.now(jst)
    env.time = now.strftime('%Y.%m.%d_%H.%M.%S')

    env.current_release = '%(releases_path)s/%(time)s' % env
    with cd(env.releases_path):
        return run('git clone -q -o deploy --depth 1 %(branch_option)s %(git_clone)s %(current_release)s' % env, quiet=True)

def _collectstatic():
    print 'collectstatic',
    sys.stdout.flush()
    if not env.has_key('current_path'):
        _releases()
    with cd('%(current_path)s/%(app_name)s' % env):
        r = run('%(activate)s; python manage.py collectstatic --noinput' % env, quiet=True)
    _print_result(r)

def _grunt_build():
    print 'grunt build',
    sys.stdout.flush()
    if not env.has_key('current_path'):
        _releases()
    with cd('%(current_path)s/angular' % env):
        r = []
        r.append(run('npm install', quiet=True))
        r.append(run('bower install', quiet=True))
        r.append(run('grunt build', quiet=True))
        r.append(run('ln -nfs ../../%(app_name)s/assets dist/static' % env, quiet=True))
    _print_result(r)

def _compilemessages():
    print 'compilemessages',
    sys.stdout.flush()
    if not env.has_key('current_path'):
        _releases()
    with cd('%(current_path)s/%(app_name)s' % env):
        r = run('%(activate)s; python manage.py compilemessages' % env, quiet=True)
    _print_result(r)

def _update():
    """Copies your project and updates environment and symlink"""
    _update_code()
    symlink()
    _update_env()
    _collectstatic()
    _grunt_build()
    #_compilemessages()

def _update_code():
    """Copies your project to the remote servers"""
    print 'git clone', env.branch_option,
    sys.stdout.flush()
    try:
        r = _checkout()
    except:
        r = _checkout()
    _permissions()
    _print_result(r)

def symlink():
    """Updates the symlink to the most recently deployed version"""
    _releases()
    run('ln -nfs %(current_release)s %(current_path)s' % env, quiet=True)
    run('ln -nfs %(shared_path)s/media %(current_release)s/%(app_name)s/' % env, quiet=True)
    run('ln -nfs %(shared_path)s/node_modules %(current_release)s/angular/' % env, quiet=True)
    run('ln -nfs %(shared_path)s/bower_components %(current_release)s/angular/' % env, quiet=True)

def _update_env():
    """Update servers environment on the remote servers"""
    if not env.has_key('current_path'):
        _releases()

    with cd(env.current_path):
        run('%(activate)s; pip install -r %(pip_file)s' % env, quiet=True)

def _migrate():
    """south migrate"""
    print 'migrate',
    sys.stdout.flush()
    if not env.has_key('current_path'):
        _releases()
    with cd('%(current_path)s/%(app_name)s' % env):
        r = run('%(activate)s; python manage.py migrate' % env, quiet=True)
    _print_result(r)

def cleanup():
    """Clean up old releases"""
    if not env.has_key('releases'):
        _releases()
    if len(env.releases) > 3:
        directories = env.releases
        directories.reverse()
        del directories[:3]
        env.directories = ' '.join([ '%(releases_path)s/%(release)s' % { 'releases_path':env.releases_path, 'release':release } for release in directories ])
        run('rm -rf %(directories)s' % env, quiet=True)

def _rollback_code():
    """Rolls back to the previously deployed version"""
    _releases()
    if len(env.releases) >= 2:
        env.current_release = env.releases[-1]
        env.previous_revision = env.releases[-2]
        env.current_release = '%(releases_path)s/%(current_revision)s' % env
        env.previous_release = '%(releases_path)s/%(previous_revision)s' % env
        run('rm %(current_path)s; ln -s %(previous_release)s %(current_path)s && rm -rf %(current_release)s' % env, quiet=True)

def rollback():
    """Rolls back to a previous version and restarts"""
    _rollback_code()
    restart()

def cold():
    """Deploys and starts a `cold' application"""
    _update()
    _migrate()
    restart()

def branch(branch):
    """django-dbdump & cold on branch
    usage:
      fab staging branch:setup-copyable-staging
    """
    env.branch_option = '-b %s --single-branch' % branch
    dbdump()
    cold()

def deploy():
    """Deploys your project. This calls both `update' and `restart'"""
    _update()
    restart()

def _print_result(r):
    if isinstance(r, list):
        for rr in r:
            if not rr.succeeded:
                print(colors.red('FAILED'))
                print(colors.magenta(rr))
                raise
        print(colors.green('OK'))
        return

    if r.succeeded:
        print(colors.green('OK'))
    else:
        print(colors.red('FAILED'))
        print(colors.magenta(r))
        raise
