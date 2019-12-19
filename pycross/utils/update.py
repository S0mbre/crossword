# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import datetime
from pathlib import Path, PurePath
import os, sys, subprocess, json, shutil, argparse

ENCODING = 'utf-8'
GIT_ERROR = 'You do not appear to have a valid version of git installed!\nPlease install git from https://git-scm.com/'
PIP_INSTALL = 'install --upgrade --src="{}" -e git+{}@{}#egg={}'

class Updater:

    def __init__(self, app_name, app_version, git_repo, update_file,
                 check_every=1, check_major_versions=True, src_dir='', 
                 on_get_recent=None, on_before_update=None, on_norecent=None,
                 on_update_log=None, on_update_error=None):

        self.app_name = app_name
        self.app_version = app_version
        self.git_repo = git_repo
        self.update_file = Path(update_file).resolve()
        print(f"Update file = {str(self.update_file)}")
        self.check_every = check_every
        self.check_major_versions = check_major_versions
        self.src_dir = Path(src_dir).resolve() if src_dir else Path(__file__).resolve().parents[2]
        print(f"Src = {str(self.src_dir)}")
        self.on_get_recent = on_get_recent
        self.on_before_update = on_before_update
        self.on_norecent = on_norecent
        self.on_update_log = on_update_log
        self.on_update_error = on_update_error
        self.update_info = {'last_update': '', 'last_check': '', 
                            'recent_version': {'version': '', 'hash': '', 'branch': '',
                                               'description': '', 'date': ''}}
        self.git_installed = self._check_git()        
        self._init_update_info()

    def _run_exe(self, args, external=False, capture_output=True, encoding=ENCODING, 
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=None, shell=False, **kwargs):
        if external:
            return subprocess.Popen(args, 
                creationflags=(subprocess.DETACHED_PROCESS | creationflags), 
                encoding=encoding, shell=shell, **kwargs)
        else:
            return subprocess.run(args, 
                capture_output=capture_output, encoding=encoding, 
                timeout=timeout, shell=shell, **kwargs)

    def _datetime_to_str(self, dt=None, strformat='%Y-%m-%d %H-%M-%S'):
        if dt is None: dt = datetime.now()
        return dt.strftime(strformat)

    def _str_to_datetime(self, text, strformat='%Y-%m-%d %H-%M-%S'):
        return datetime.strptime(text, strformat)

    def _check_git(self):
        try:
            res = self._run_exe(['git', '--version'])
            return res.returncode == 0
        except:
            return False

    def _init_update_info(self):
        if self.update_file.exists():
             with open(str(self.update_file), 'r', encoding=ENCODING) as infile:
                self.update_info.update(json.load(infile))
            
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

    def _get_remote_branches(self, exclude_starting_with=('master',), include_starting_with=('release',)):
        if not self.git_installed: return None
        res = self._run_exe(['git', 'ls-remote', '--heads'])
        res = res.stdout.strip().splitlines()
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
        res = self._run_exe(['git', 'log', '-1', '--format=%at', recent_br[1][0]])
        date_ts = res.stdout.strip()

        return {'version': ''.join(recent_br[0]), 'hash': recent_br[1][1], 
                'branch': recent_br[1][0], 'description': '', 
                'date': self._datetime_to_str(datetime.fromtimestamp(int(date_ts))) if date_ts else ''}

    def _run_pip(self, *pip_commands):
        args = [sys.executable, '-m', 'pip'] + list(pip_commands)
        return self._run_exe(args)
    
    def _update_from_branch(self, branch_name):
        if not branch_name or not self.git_installed: return None
        res = self._run_pip('install', '--upgrade', f'--src="{self.src_dir}"',
                            '-e', f'git+{self.git_repo}@{branch_name}#egg={self.app_name}')
        out = res.stdout.strip()
        err = res.stderr.strip()
        if out and self.on_update_log:
            self.on_update_log(out)
        if err and self.on_update_error:
            self.on_update_error(err)
        return res

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
            #print(recent_vers['error'])
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

        self.update_info['last_update'] = self._datetime_to_str()
        self._write_update_info()
        
        res = self._update_from_branch(vers['branch'])
        return res.returncode == 0

    def copyself(self, dest):
        """
        Copies this file (update.py) to the given folder (dest).
        Returns the full destination file path on success and None otherwise.
        """
        this_file = Path(__file__).resolve()
        new_path = Path(PurePath.joinpath(Path(dest).resolve(), this_file.name))

        print(f"Copying '{str(this_file)}' to '{str(new_path)}'...")
        #new_path.replace(this_file)
        try:
            new_path.unlink()
        except:
            pass
        shutil.copy(str(this_file), str(new_path))
        return str(new_path) if new_path.exists() else None
    

    
## ******************************************************************************** ##

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('appname', help='Application name')
    parser.add_argument('version', help='Application current version, e.g. "0.1"')
    parser.add_argument('repo', help='Git repo url, e.g. "https://github.com/.../project.git"')
    parser.add_argument('updatefile', help='Full or relative path to update.json')
    parser.add_argument('-m', '--major', action='store_true', help='Check only major versions')
    parser.add_argument('-c', '--copy', default='', help='Directory to copy this file to')
    parser.add_argument('-s', '--source', default='', help='Path to app source directory (containing .git directory)')
    parser.add_argument('-u', '--update', action='store_true', help='Start updating app')
    parser.add_argument('-d', '--deleteself', action='store_true', help='Commit suicide ater completon')
    args_obj = parser.parse_args()

    updater = Updater(args_obj.appname, args_obj.version, args_obj.repo, args_obj.updatefile,
        check_major_versions=args_obj.major, src_dir=args_obj.source,
        on_update_log=lambda out: print(out), on_update_error=lambda out: print(out))

    if args_obj.copy:
        new_file = updater.copyself(args_obj.copy)
        if not new_file:
            return
        args = [sys.executable, f'\"{new_file}\"', 
            args_obj.appname, args_obj.version, args_obj.repo, f'\"{updater.update_file}\"', '-d']
        args.append(f'-s=\"{str(updater.src_dir)}\"')
        if args_obj.major: args.append('-m')
        if args_obj.update: args.append('-u')
        args += ['>', f'\"{args_obj.copy}\\1.txt\"']
        print(' '.join(args))

        updater._run_exe(args, True)
        return

    print(f"Hello from '{__file__}'!")
    print(os.getcwd())
    print(updater.check_update(True))

    if args_obj.deleteself:
        print('Deleting myself...')

## ******************************************************************************** ##

if __name__ == '__main__':
    sys.exit(main())




