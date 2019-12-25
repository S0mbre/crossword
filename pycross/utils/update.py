# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import datetime
from pathlib import Path, PurePath
import os, sys, subprocess, json, traceback

ENCODING = 'utf-8'
GIT_ERROR = 'You do not appear to have a valid version of git installed!\nPlease install git from https://git-scm.com/'

class Updater:

    def __init__(self, app_name, app_version, git_repo, update_file, log_file,
                 check_every=1, check_major_versions=True,  
                 on_get_recent=None, on_before_update=None, on_norecent=None,
                 print_to=sys.stdout):

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
        self.git_installed = self._check_git()        
        self._init_update_info()

    def _run_exe(self, args, external=False, capture_output=True, encoding=ENCODING, 
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=None, shell=False, **kwargs):
        try:
            if external:
                return subprocess.Popen(args, 
                    creationflags=(subprocess.DETACHED_PROCESS | creationflags), 
                    stdout=self.print_to, stderr=subprocess.STDOUT,
                    encoding=encoding, shell=shell, **kwargs) if capture_output else \
                       subprocess.Popen(args, 
                    creationflags=(subprocess.DETACHED_PROCESS | creationflags), 
                    encoding=encoding, shell=shell, **kwargs)
            else:
                return subprocess.run(args, 
                    capture_output=capture_output, encoding=encoding, 
                    timeout=timeout, shell=shell, **kwargs)
        except Exception as err:
            traceback.print_exc(file=self.print_to)
            raise

    def _datetime_to_str(self, dt=None, strformat='%Y-%m-%d %H-%M-%S'):
        if dt is None: dt = datetime.now()
        return dt.strftime(strformat)

    def _str_to_datetime(self, text, strformat='%Y-%m-%d %H-%M-%S'):
        return datetime.strptime(text, strformat)

    def _check_git(self):
        try:
            res = self._run_exe(['git', 'status'])
            return res.returncode == 0
        except:
            return False

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
        if max_versions > 0:
            return tuple([int(v) for v in version_str.split('.')][:max_versions])
        else:
            return tuple([int(v) for v in version_str.split('.')])

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

    def _run_git(self, *args, **kwargs):
        gitargs = ['git'] + list(args)
        print(f"Running {' '.join(gitargs)}...", file=self.print_to)
        return self._run_exe(gitargs, **kwargs)

    def _get_remote_branches(self, exclude_starting_with=('master',), include_starting_with=('release',)):
        if not self.git_installed: return None
        res = self._run_git('ls-remote', '--heads')        
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
            branches[self._parse_version(br)] = (br, entry[0])
        return branches

    def _get_recent_version(self):
        if not self.git_installed: return {'error': GIT_ERROR}
        branches = self._get_remote_branches()
        if not branches:
            return {'error': 'No release branches in repository!'}

        # make sorted list, where latest version will be at top
        branches = sorted(branches.items(), key=lambda t: t[0], reverse=True)        
        # get latest
        recent_br = branches[0]
        # get date
        res = self._run_git('log', '-1', '--format=%at', recent_br[1][1])
        date_ts = res.stdout.strip()

        return {'version': self._strip_version_az(recent_br[1][0]), 
                'hash': recent_br[1][1], 
                'branch': recent_br[1][0], 'description': '', 
                'date': self._datetime_to_str(datetime.fromtimestamp(int(date_ts))) if date_ts else ''}
    
    def _update_from_branch(self, branch_or_commit):
        if not branch_or_commit or not self.git_installed: return

        shellfile = PurePath.joinpath(Path(__file__).parent, 'update.bat' if sys.platform.startswith('win') else 'update.sh')
        logfile = f' > "{self.log_file}"' if self.log_file else ''
        args = f'{str(shellfile)} {branch_or_commit}{logfile}'
        #print(args, file=self.print_to)
        self._run_exe(args, external=True, capture_output=False, shell=True)

    def _update_check_required(self):
        dt_now = datetime.now()
        dt_lastcheck = self._str_to_datetime(self.update_info['last_check']) if self.update_info['last_check'] else None
        return dt_lastcheck is None or \
               (self.check_every > 0 and (dt_now - dt_lastcheck).days >= self.check_every)

    def check_update(self, force=False):
        if not force and not self._update_check_required():
            return None
        recent_vers = self._get_recent_version()        
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

    def update(self, force=False):
        vers = self.check_update(force)
        if not vers: 
            if self.on_norecent: self.on_norecent()
            return False

        if self.on_before_update and not self.on_before_update(self.app_version, vers): 
            return False

        #self.update_info['last_update'] = self._datetime_to_str()
        #self._write_update_info()   
        self._update_from_branch(vers['hash'])


