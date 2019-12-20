# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import datetime
from pathlib import Path, PurePath
import os, sys, subprocess, json, shutil, argparse, traceback

ENCODING = 'utf-8'
GIT_ERROR = 'You do not appear to have a valid version of git installed!\nPlease install git from https://git-scm.com/'
PIP_INSTALL = 'install --upgrade --src="{}" -e git+{}@{}#egg={}'

class Updater:

    def __init__(self, app_name, app_version, git_repo, update_file,
                 check_every=1, check_major_versions=True, src_dir='', 
                 on_get_recent=None, on_before_update=None, on_norecent=None,
                 on_update_log=None, on_update_error=None, print_to=sys.stdout):

        self.app_name = app_name
        self.app_version = app_version
        self.git_repo = git_repo
        self.update_file = Path(update_file).resolve()
        self.print_to = print_to
        #print(f"Update file = {str(self.update_file)}", file=self.print_to)
        self.check_every = check_every
        self.check_major_versions = check_major_versions
        self.src_dir = Path(src_dir).resolve() if src_dir else Path(__file__).resolve().parents[2]
        self.git_dir = PurePath.joinpath(self.src_dir, PurePath('.git/'))
        #print(f"Git dir = {str(self.git_dir)}", file=self.print_to)
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
        try:
            if external:
                return subprocess.Popen(args, 
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

    def _run_git(self, *args):
        gitargs = ['git', f'--git-dir={str(self.git_dir)}']
        gitargs += list(args)
        print(f"Running {' '.join(gitargs)}...", file=self.print_to)
        return self._run_exe(gitargs)

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

    def _run_pip(self, *pip_commands):
        args = [sys.executable, '-m', 'pip'] + list(pip_commands)
        print(f"Running {' '.join(args)}...", file=self.print_to)
        return self._run_exe(args, capture_output=False, 
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=None)
    
    def _update_from_branch(self, branch_name):
        if not branch_name or not self.git_installed: return None
        os.chdir(os.path.abspath(os.sep))
        print(f"Working dir = '{os.getcwd()}'", file=self.print_to)

        
        res = self._run_pip('install', '--upgrade', f'--src="{str(self.src_dir.parents[0])}"', '-I', '-qqq',
                            '-e', f'git+{self.git_repo}@{branch_name}#egg={str(self.src_dir.name)}')
        
        """
        sout = res.stdout.strip()
        serr = res.stderr.strip()

        if sout and self.on_update_log:
            self.on_update_log(sout)
        if serr and self.on_update_error:
            self.on_update_error(serr)
        """

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
        
        res = self._update_from_branch(vers['branch'])
        print(f"Result = {res.returncode}", file=self.print_to)
        ok = (res.returncode == 0)
        if ok:
            self.update_info['last_update'] = self._datetime_to_str()
            self._write_update_info()

        return ok

    def copyself(self, dest):
        """
        Copies this file (update.py) to the given folder (dest).
        Returns the full destination file path on success and None otherwise.
        """
        this_file = Path(__file__).resolve()
        new_path = Path(PurePath.joinpath(Path(dest).resolve(), this_file.name))

        #print(f"Copying '{str(this_file)}' to '{str(new_path)}'...", file=self.print_to)
        #new_path.replace(this_file)
        try:
            new_path.unlink()
        except:
            pass
        shutil.copy(str(this_file), str(new_path))
        return str(new_path) if new_path.exists() else None
    

    
## ******************************************************************************** ##

def main():

    def QUOTEME(path):
        return f'\"{path}\"'

    parser = argparse.ArgumentParser()
    parser.add_argument('appname', help='Application name')
    parser.add_argument('version', help='Application current version, e.g. "0.1"')
    parser.add_argument('repo', help='Git repo url, e.g. "https://github.com/.../project.git"')
    parser.add_argument('updatefile', help='Full or relative path to update.json')
    parser.add_argument('-m', '--major', action='store_true', help='Check only major versions')
    parser.add_argument('-c', '--copy', default='', help='Directory to copy this file to')
    parser.add_argument('-s', '--source', default='', help='Path to app source directory (containing .git directory)')
    parser.add_argument('-u', '--update', action='store_true', help='Start updating app')
    parser.add_argument('-o', '--output', default='', help='Path to output file for console output (empty = STDOUT)')
    parser.add_argument('-r', '--restart', default='', help='Path to cwordg.py to restart (if empty the app will not be restarted)')
    args_obj = parser.parse_args()

    out_file = sys.stdout
    if args_obj.output:
        args_obj.output = Path(args_obj.output).resolve()
        out_file = open(str(args_obj.output), 'a' if args_obj.copy else 'w', encoding=ENCODING)

    print(f"Running with {vars(args_obj)} ...", file=out_file)

    try:
        updater = Updater(args_obj.appname, args_obj.version, args_obj.repo, args_obj.updatefile,
            check_major_versions=args_obj.major, src_dir=args_obj.source,
            on_update_log=lambda out: print(out, file=out_file), 
            on_update_error=lambda out: print(out, file=out_file),
            print_to=out_file)

        if args_obj.copy:
            new_file = updater.copyself(args_obj.copy)
            if not new_file: 
                raise Exception('Could not copy update.py to new location!')
            args = [QUOTEME(sys.executable), QUOTEME(new_file), 
                args_obj.appname, args_obj.version, args_obj.repo, QUOTEME(updater.update_file)]
            args.append('-s ' + QUOTEME(str(updater.src_dir)))
            if args_obj.major: args.append('-m')
            if args_obj.update: args.append('-u')
            if args_obj.restart: args.append('-r ' + QUOTEME(str(Path(args_obj.restart).resolve())))
            args.append('-o ' + QUOTEME(str(args_obj.output)))
            s_args = ' '.join(args)
            print(f"Running {s_args}...", file=out_file)
            updater._run_exe(s_args, True, shell=True)
            print(f"Exiting '{__file__}'...\n\n", file=out_file)
            if args_obj.output: out_file.close()
            return

        if args_obj.update:

            def on_norecent():
                print('No recent versions found on server!', file=out_file)

            def on_before_update(old_version, new_version):
                print(f"Updating from version {old_version} to {new_version['version']}...", file=out_file)
                return True
                        
            updater.on_norecent = on_norecent
            updater.on_before_update = on_before_update
            updater.update(True)
            updater._write_update_info()

            if args_obj.restart:
                args = [QUOTEME(sys.executable), QUOTEME(args_obj.restart)]
                s_args = ' '.join(args)
                os.chdir(updater.src_dir)
                updater._run_exe(s_args, True, shell=True)

        print(f"Exiting '{__file__}'...", file=out_file)

    except Exception as err:
        print(str(err), file=out_file)

    finally:
        if args_obj.output: out_file.close()

## ******************************************************************************** ##

if __name__ == '__main__':
    sys.exit(main())




