# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.update
import os, sys, subprocess, json, traceback, platform
from datetime import datetime
from pathlib import Path, PurePath
from .globalvars import *

ENCODING = 'utf-8'
GIT_ERROR = _('You do not appear to have a valid version of git installed!\nPlease install git from https://git-scm.com/')
NOTHING_INSTALLED_ERROR = _('Neither Git nor the python package is installed!')

class Updater:

    def __init__(self, app_name, app_version, git_repo, update_file, log_file,
                 check_every=1, check_major_versions=True, git_exe=None,  
                 on_get_recent=None, on_before_update=None, on_norecent=None,
                 print_to=sys.stdout):

        thisfile = os.path.abspath(__file__)
        if not thisfile.startswith(os.path.abspath(os.getcwd())):
            cd = os.path.dirname(os.path.dirname(thisfile))
            os.chdir(cd)

        self.app_name = app_name
        self.app_version = app_version
        self.git_repo = git_repo
        self.update_file = Path(update_file).resolve()
        self.log_file = Path(log_file).resolve()
        self.print_to = print_to
        #print(f"Update file = {str(self.update_file)}", file=self.print_to)
        self.check_every = check_every
        self.check_major_versions = check_major_versions
        self.on_get_recent = on_get_recent
        self.on_before_update = on_before_update
        self.on_norecent = on_norecent
        self.update_info = {'last_update': '', 'last_check': '', 
                            'recent_version': {'version': '', 'hash': '', 'branch': '',
                                               'description': '', 'date': ''}}
        self.git_exe = git_exe or 'git'
        self.git_installed = self._git_check_installed() and self._git_check_repo()
        self.pkg_installed = self._pip_check_pkg_installed()
        self._init_update_info()

    def update(self, force=False):
        if not self.git_installed and not self.pkg_installed:
            print(NOTHING_INSTALLED_ERROR, file=self.print_to)
            return False

        vers = self.check_update(force)
        if not vers: 
            if self.on_norecent: self.on_norecent()
            return False

        if self.on_before_update and not self.on_before_update(self.app_version, vers): 
            return False

        #self.update_info['last_update'] = self._datetime_to_str()
        #self._write_update_info()   
        if self.git_installed:
            self._git_update_from_branch(vers['hash'])
        else:
            self._pip_update()

    def check_update(self, force=False):
        if not self.git_installed and not self.pkg_installed:
            print(NOTHING_INSTALLED_ERROR, file=self.print_to)
            return None

        if not force and not self._update_check_required():
            return None

        recent_vers = self.get_recent_version()
        if 'error' in recent_vers:
            print(recent_vers['error'], file=self.print_to)
            return None

        res = None
        if self._compare_versions(self.app_version, recent_vers['version'], 
                                 self.check_major_versions) == '<':
            res = recent_vers

        if self.on_get_recent and res and not self.on_get_recent(res):
            return None

        self.update_info['last_check'] = self._datetime_to_str()
        self.update_info['recent_version'] = res or ''
        self._write_update_info()

        return res

    def get_recent_version(self):
        if self.git_installed:
            return self._git_get_recent_version()
        elif self.pkg_installed:
            return self._pip_get_recent_version()
        else:
            return {'error': NOTHING_INSTALLED_ERROR}

    def _update_check_required(self):        
        dt_now = datetime.now()
        dt_lastcheck = self._str_to_datetime(self.update_info['last_check']) if self.update_info['last_check'] else None
        return dt_lastcheck is None or \
               (self.check_every > 0 and (dt_now - dt_lastcheck).days >= self.check_every)

    def _git_check_installed(self):
        try:
            res = self._git_run('--version')
            return res.returncode == 0
        except:
            return False

    def _git_check_repo(self):
        try:
            res = self._git_run('status')            
            return res.returncode == 0
        except:
            return False

    def _git_run(self, *args, **kwargs):
        gitargs = [self.git_exe] + list(args)
        if DEBUGGING:
            print(_("Running {}...").format((' '.join(gitargs))), file=self.print_to)
        return self._run_exe(gitargs, **kwargs)

    def _git_update_from_branch(self, branch_or_commit):
        if not branch_or_commit or not self.git_installed: return

        shellfile = PurePath.joinpath(Path(__file__).parent, f"update_git.{'bat' if sys.platform.startswith('win') else 'sh'}")
        logfile = f' > "{self.log_file}"' if self.log_file else ''
        args = f'{str(shellfile)} {branch_or_commit}{logfile}'
        #print(args, file=self.print_to)
        self._run_exe(args, external=True, capture_output=False, shell=True)

    def _git_get_remote_branches(self, exclude_starting_with=('master',), include_starting_with=('release',)):
        if not self.git_installed: return None
        res = self._git_run('ls-remote', '--heads')        
        res = res.stdout.strip().splitlines()
        #print(res, file=self.print_to)
        branches = {}
        for l in res:
            entry = l.split()
            if len(entry) != 2: continue
            br = entry[1].split('/')[-1]
            include = True
            if exclude_starting_with:
                for e in exclude_starting_with:
                    if br.startswith(e):
                        include = False
                        break
            if not include: continue
            include = False
            if include_starting_with:
                for i in include_starting_with:
                    if br.startswith(i):
                        include = True
                        break
            if not include: continue
            parsed = self._parse_version(br)
            if not parsed is None:
                branches[parsed] = (br, entry[0])
        return branches

    def _git_get_recent_version(self):
        if not self.git_installed: return {'error': GIT_ERROR}
        branches = self._git_get_remote_branches()
        if not branches:
            return {'error': _('No release branches in repository!')}

        # make sorted list, where latest version will be at top
        branches = sorted(branches.items(), key=lambda t: t[0], reverse=True)        
        # get latest
        recent_br = branches[0]
        # get date
        res = self._git_run('log', '-1', '--format=%at', recent_br[1][1])
        date_ts = res.stdout.strip()

        return {'version': self._strip_version_az(recent_br[1][0]), 
                'hash': recent_br[1][1], 
                'branch': recent_br[1][0], 'description': '', 
                'date': self._datetime_to_str(datetime.fromtimestamp(int(date_ts))) if date_ts else ''}

    def _pip_run(self, *args, **kwargs):
        pipargs = ['python', '-m', 'pip'] + list(args)
        if DEBUGGING:
            print(_("Running {}...").format((' '.join(pipargs))), file=self.print_to)
        return self._run_exe(pipargs, **kwargs)

    def _pip_list_packages(self, outdated_only=False):
        if outdated_only:
            args = ('list', '--format=json', '-o')
        else:
            args = ('list', '--format=json')
        pkg_list = self._pip_run(*args)
        if pkg_list.returncode:
            print(pkg_list.stderr or _('{} completed with error!').format(' '.join(args)), file=self.print_to)
            return []
        try:
            pkg_list = json.loads(pkg_list.stdout)
            # the returned results is a list of dictionaries: [{'name': pk_name, 'version': pk_version}, ...]
            # if outdated_only == False, each dict contains 2 elements: 'name' and 'version'
            # if outdated_only == True, 2 additional keys are present: 'latest_version' and 'latest_filetype'        
            return pkg_list
        except json.JSONDecodeError as err:
            print(_('{}\nat line {}, column {}').format(err.msg, err.lineno, err.colno), file=self.print_to)
            return []

    def _pip_check_pkg_installed(self):
        pkg_list = self._pip_list_packages()
        for pk in pkg_list:
            if pk['name'] == APP_NAME:
                return True
        return False

    def _pip_update(self):
        if not self.pkg_installed: return

        shellfile = PurePath.joinpath(Path(__file__).parent, f"update_pip.{'bat' if sys.platform.startswith('win') else 'sh'}")
        logfile = f' > "{self.log_file}"' if self.log_file else ''
        args = f'{str(shellfile)} {logfile}'
        #print(args, file=self.print_to)
        self._run_exe(args, external=True, capture_output=False, shell=True)
    
    def _pip_get_recent_version(self):
        pkg_list = self._pip_list_packages(True)
        v = {'hash': '', 'branch': '', 'description': '', 'date': ''}
        for pk in pkg_list:
            if pk['name'] == APP_NAME:
                v['version'] = pk['latest_version']
                return v
        v['version'] = self.app_version
        return v

    def _run_exe(self, args, external=False, capture_output=True, stdout=subprocess.PIPE, encoding=ENCODING, 
                timeout=None, shell=False, **kwargs):
        try:
            osname = platform.system()        
            if external:
                if osname == 'Windows':
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                    return subprocess.Popen(args, 
                        creationflags=creationflags, 
                        stdout=stdout if capture_output else None, 
                        stderr=subprocess.STDOUT if capture_output else None,
                        encoding=encoding, shell=shell, **kwargs)
                else: # assume Unix
                    return subprocess.Popen('nohup ' + (args if isinstance(args, str) else ' '.join(args)), 
                        stdout=stdout if capture_output else None, 
                        stderr=subprocess.STDOUT if capture_output else None,
                        encoding=encoding, shell=shell, preexec_fn=os.setpgrp,
                        **kwargs)
            else:
                return subprocess.run(args, 
                    capture_output=capture_output, encoding=encoding, 
                    timeout=timeout, shell=shell, **kwargs)
        except Exception as err:
            traceback.print_exc(limit=None)
            raise

    def _datetime_to_str(self, dt=None, strformat='%Y-%m-%d %H-%M-%S'):
        if dt is None: dt = datetime.now()
        return dt.strftime(strformat)

    def _str_to_datetime(self, text, strformat='%Y-%m-%d %H-%M-%S'):
        return datetime.strptime(text, strformat)

    def _init_update_info(self):
        if self.update_file.exists():
             with open(str(self.update_file), 'r', encoding=ENCODING) as infile:
                self.update_info.update(json.load(infile))
        else:
            self._write_update_info()
            
    def _write_update_info(self):
        with open(str(self.update_file), 'w', encoding=ENCODING) as outfile:
            json.dump(self.update_info, outfile, ensure_ascii=False, indent='\t')

    def _strip_version_az(self, version_str):
        return ''.join([c for c in version_str if c in list('0123456789.')])

    def _parse_version(self, version_str, max_versions=-1):
        version_str = self._strip_version_az(version_str)
        try:
            if max_versions > 0:
                return tuple([int(v) for v in version_str.split('.')][:max_versions])
            else:
                return tuple([int(v) for v in version_str.split('.')])
        except:
            # version string is incorrectly formatted
            return None

    def _compare_versions(self, v1, v2, max_versions=-1, major_only=False):
        tv1 = self._parse_version(v1, max_versions)
        tv2 = self._parse_version(v2, max_versions)        
        l = min(len(tv1), len(tv2))
        if major_only: l = min(l, 1)
        tv1 = tv1[:l] 
        tv2 = tv2[:l] 
        if tv1 < tv2: return '<'
        if tv1 > tv2: return '>'
        return '='
    


