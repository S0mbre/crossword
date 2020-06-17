# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.update
# Support for application updates from the PyPi or Github servers.
import os, sys, subprocess, json, traceback, platform
from datetime import datetime
from pathlib import Path, PurePath
from .globalvars import *

## `str` default encoding used in executable calls
ENCODING = 'utf-8'
## `str` error message displayed when the app fails to find a Git installation
GIT_ERROR = _('You do not appear to have a valid version of git installed!\nPlease install git from https://git-scm.com/')
## `str` error message displayed when the app fails to find either Git or the PyPi package
NOTHING_INSTALLED_ERROR = _('Neither Git nor the python package is installed!')

## @brief Class responsible for application updating and checking new available releases.
# It allows for two checking / updating methods:
#   1. From the Gihub repository using [git](https://git-scm.com/).
#   2. From the PyPi repository using [pip](https://pip.pypa.io/en/stable/).
# The method is chosen automatically, depending on whether the app has been
# installed with pip as a Python package or is contained in a local Git repo.
class Updater:

    ## @param app_name `str` this application name (see `globalvars::APP_NAME`)
    # @param app_version `str` this application version (see `globalvars::APP_VERSION`)
    # @param git_repo `str` the Git host (see `globalvars::GIT_REPO`)
    # @param update_file `str` path to the update log file (see `globalvars::UPDATE_FILE`)
    # @param log_file `str` path to the debug log file (to output messages)
    # @param check_every `int` interval in days to check for updates
    # @param check_major_versions `bool` whether to check only for major
    # releases (e.g. 1.0... 2.0...) or all (including minor) releases
    # @param git_exe `str` path to the Git executable (`None` means the simple
    # string 'git' will be used, i.e. Git must be in the system path)
    # @param on_get_recent `callable` callback fired when a new release
    # is detected. The callback takes one argument:
    #   * `dict` the new version info (see check_update() return value)
    # @param on_before_update `callable` callback fired before the app
    # updating process starts. Its prototype is as follows:
    # ```
    # (current_version: str, new_version: dict) -> bool
    # ```
    # Args:
    #   * current_version `str` the current app version, e.g. '2.0'
    #   * new_version `dict` the new app version, e.g. `{'version': '2.1', 'hash': '', 'branch': '', 'description': '', 'date': ''}`
    # Returns:
    #   * `bool` `True` to continue update; `False` to abort
    # @param on_norecent `callable` callback fired when no updates are available;
    # the callbacks takes no arguments and returns nothing
    # @param print_to `file` file-like object to output messages to
    # (default = `sys.stdout`, the system console output)
    def __init__(self, app_name, app_version, git_repo, update_file, log_file,
                 check_every=1, check_major_versions=True, git_exe=None,
                 on_get_recent=None, on_before_update=None, on_norecent=None,
                 print_to=sys.stdout):

        thisfile = os.path.abspath(__file__)
        if not thisfile.startswith(os.path.abspath(os.getcwd())):
            cd = os.path.dirname(os.path.dirname(thisfile))
            os.chdir(cd)

        ## `str` this application name (see `globalvars::APP_NAME`)
        self.app_name = app_name
        ## `str` this application version (see `globalvars::APP_VERSION`)
        self.app_version = app_version
        ## `str` the Git host (see `globalvars::GIT_REPO`)
        self.git_repo = git_repo
        ## `str` full path to the update log file (see `globalvars::UPDATE_FILE`)
        self.update_file = Path(update_file).resolve()
        ## `str` full path to the debug log file (to output messages)
        self.log_file = Path(log_file).resolve()
        ## `file` file-like object to output messages to
        self.print_to = print_to
        #print(f"Update file = {str(self.update_file)}", file=self.print_to)
        ## `int` interval in days to check for updates
        self.check_every = check_every
        ## `bool` whether to check only for major
        # releases (e.g. 1.0... 2.0...) or all (including minor) releases
        self.check_major_versions = check_major_versions
        ## `callable` callback fired when a new release is detected
        self.on_get_recent = on_get_recent
        ## `callable` callback fired before the app updating process starts
        self.on_before_update = on_before_update
        ## `callable` callback fired when no updates are available
        self.on_norecent = on_norecent
        ## @brief `dict` update info stored in the update file
        # The items are as follows:
        #   * last_update `str` date and time of the last update (as a string)
        #   * last_check `str` date and time of the last update check (as a string)
        #   * recent_version `dict` info on the latest available release:
        #       * version `str` app version string (e.g. '3.0')
        #       * hash `str` Git commit hash corresponding to the version (only for Github updates)
        #       * branch `str` Git branch name corresponding to the version (only for Github updates)
        #       * description `str` optional description of the latest release (only for Github updates)
        #       * date `str` date and time of the Git commit (only for Github updates)
        self.update_info = {'last_update': '', 'last_check': '',
                            'recent_version': {'version': '', 'hash': '', 'branch': '',
                                               'description': '', 'date': ''}}
        ## `str` path to the Git executable
        # @warning `None` means the simple string 'git' will be used,
        # i.e. Git must be in the system path
        self.git_exe = git_exe or 'git'
        ## `bool` `True` if Git is installed in the current system
        self.git_installed = self._git_check_installed() and self._git_check_repo()
        ## `bool` `True` if the app is currently installed via pip (from PyPi)
        self.pkg_installed = self._pip_check_pkg_installed() if not self.git_installed else False
        self._init_update_info()

    ## Updates the application to the most recent version.
    # @param force `bool` if set to `True`, the update will proceed
    # regardless of the update check interval
    # @returns `bool` `False` on failure, `None` on success
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

    ## @brief Checks for the latest app version available on Github or PyPi.
    # This method also updates the update.log file so the application
    # can read the release info on next startup.
    # @param force `bool` check regardless of the update check interval
    # @returns `dict` | `None` latest version info or `None` on failure.
    # The version info dict contains the following items:
    #   * version `str` app version string (e.g. '3.0')
    #   * hash `str` Git commit hash corresponding to the version (only for Github updates)
    #   * branch `str` Git branch name corresponding to the version (only for Github updates)
    #   * description `str` optional description of the latest release (only for Github updates)
    #   * date `str` date and time of the Git commit (only for Github updates)
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

    ## Retrieves information on the latest app version available on Github or PyPi.
    # @returns `dict` latest version info.
    # The version info dict contains the following items:
    #   * version `str` app version string (e.g. '3.0')
    #   * hash `str` Git commit hash corresponding to the version (only for Github updates)
    #   * branch `str` Git branch name corresponding to the version (only for Github updates)
    #   * description `str` optional description of the latest release (only for Github updates)
    #   * date `str` date and time of the Git commit (only for Github updates)
    # If an error occurs the resulting dictionary contains a single item:
    #   * error `str` the error message
    def get_recent_version(self):
        if self.git_installed:
            return self._git_get_recent_version()
        elif self.pkg_installed:
            return self._pip_get_recent_version()
        else:
            return {'error': NOTHING_INSTALLED_ERROR}

    ## @returns `bool` `True` if update checking is required (based on the
    # update check interval stored in the app settings); `False` if not
    # required (the app has been updated recently and the check interval
    # hasn't yet elapsed since the last update)
    def _update_check_required(self):
        dt_now = datetime.now()
        dt_lastcheck = self._str_to_datetime(self.update_info['last_check']) if self.update_info['last_check'] else None
        return dt_lastcheck is None or \
               (self.check_every > 0 and (dt_now - dt_lastcheck).days >= self.check_every)

    ## @returns `bool` `True` if Git is installed
    # (is accessible via Updater::git_exe); `False` otherwise
    def _git_check_installed(self):
        try:
            res = self._git_run('--version')
            return res.returncode == 0
        except:
            return False

    ## @returns `bool` `True` if the current directory is in a Git local repository
    # (this way we check that Git updates are possible by pulling from Github)
    def _git_check_repo(self):
        try:
            res = self._git_run('status')
            return res.returncode == 0
        except:
            return False

    ## Runs a Git command with or without arguments and returns the result.
    # @param args `positional arguments` positional arguments passed to Git
    # @param kwargs `keyword arguments` keyword arguments passed to _run_exe()
    # @returns [subprocess.CompletedProcess](https://docs.python.org/3/library/subprocess.html#subprocess.CompletedProcess) process result
    def _git_run(self, *args, **kwargs):
        gitargs = [self.git_exe] + list(args)
        if DEBUGGING:
            print(_("Running {}...").format((' '.join(gitargs))), file=self.print_to)
        return self._run_exe(gitargs, **kwargs)

    ## Updates the app from a remote Git branch or commit.
    # @param branch_or_commit `str` remote branch name or commit hash
    # @returns [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#subprocess.Popen) process result
    def _git_update_from_branch(self, branch_or_commit):
        if not branch_or_commit or not self.git_installed: return

        shellfile = PurePath.joinpath(Path(__file__).parent, f"update_git.{'bat' if sys.platform.startswith('win') else 'sh'}")
        logfile = f' > "{self.log_file}"' if self.log_file else ''
        args = f'{str(shellfile)} {branch_or_commit}{logfile}'
        #print(args, file=self.print_to)
        self._run_exe(args, external=True, capture_output=False, shell=True)

    ## Retrieves the list of remote branches for the current Git repo.
    # @param exclude_starting_with `tuple` starting strings for branch names
    # that must be excluded from the result; if `None` or empty, no
    # branches will be excluded
    # @param include_starting_with `tuple` starting strings for branch names
    # that must be included in the result; if `None` or empty, no
    # branches will be included
    # @returns `dict` remote branches found as a dictionary in the following format:
    # ```
    # {parsed_version: (branch_name, commit_hash), ...}
    # ```
    # where `parsed_version` is a tuple returned by _parse_version(),
    # `branch_name` is the branch name and `commit_hash` is the commit hash
    # to which the branch is attached
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

    ## Retrieves information on the latest app version available on Github.
    # @returns `dict` latest version info with the following items:
    #   * version `str` app version string (e.g. '3.0')
    #   * hash `str` Git commit hash corresponding to the version
    #   * branch `str` Git branch name corresponding to the version
    #   * description `str` optional description of the latest release
    #   * date `str` date and time of the Git commit
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

    ## Runs pip and returns the result.
    # @param args `positional arguments` positional arguments passed to pip
    # @param kwargs `keyword arguments` keyword arguments passed to _run_exe()
    # @returns [subprocess.CompletedProcess](https://docs.python.org/3/library/subprocess.html#subprocess.CompletedProcess) process result
    def _pip_run(self, *args, **kwargs):
        pipargs = ['python', '-m', 'pip'] + list(args)
        if DEBUGGING:
            print(_("Running {}...").format((' '.join(pipargs))), file=self.print_to)
        return self._run_exe(pipargs, **kwargs)

    ## Gets the list of installed Python packages with pip.
    # @param outdated_only `bool` if `True`, only outdated packages will be
    # included in the search result
    # @returns `list` Python packages as a list of dictionaries:
    # ```
    # [{'name': pk_name, 'version': pk_version}, ...]
    # ```
    # if `outdated_only` == `False`, each dict contains 2 elements: 'name' and 'version'
    # if `outdated_only` == `True`, 2 additional keys are present: 'latest_version' and 'latest_filetype'
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
            return pkg_list
        except json.JSONDecodeError as err:
            print(_('{}\nat line {}, column {}').format(err.msg, err.lineno, err.colno), file=self.print_to)
            return []

    ## @returns `bool` `True` if the **pycrossword** Python package
    # is installed in the current Python environment
    # (including virtualenv installation)
    def _pip_check_pkg_installed(self):
        pkg_list = self._pip_list_packages()
        for pk in pkg_list:
            if pk['name'] == APP_NAME:
                return True
        return False

    ## Updates the app from PyPi with pip.
    # @returns [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#subprocess.Popen) process result
    def _pip_update(self):
        if not self.pkg_installed: return

        shellfile = PurePath.joinpath(Path(__file__).parent, f"update_pip.{'bat' if sys.platform.startswith('win') else 'sh'}")
        logfile = f' > "{self.log_file}"' if self.log_file else ''
        args = f'{str(shellfile)} {logfile}'
        #print(args, file=self.print_to)
        self._run_exe(args, external=True, capture_output=False, shell=True)

    ## Gets the latest app version on PyPi with pip.
    # @returns latest version info.
    # The version info dict contains the following items:
    #   * version `str` app version string (e.g. '3.0')
    #   * hash `str` (EMPTY: see get_recent_version())
    #   * branch `str` (EMPTY: see get_recent_version())
    #   * description `str` (EMPTY: see get_recent_version())
    #   * date `str` (EMPTY: see get_recent_version())
    def _pip_get_recent_version(self):
        pkg_list = self._pip_list_packages(True)
        v = {'hash': '', 'branch': '', 'description': '', 'date': ''}
        for pk in pkg_list:
            if pk['name'] == APP_NAME:
                v['version'] = pk['latest_version']
                return v
        v['version'] = self.app_version
        return v

    ## Runs an executable and optionally returns the result.
    # See utils::run_exe()
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

    ## Converts a Python `datetime` object to a string.
    # See utils::datetime_to_str()
    def _datetime_to_str(self, dt=None, strformat='%Y-%m-%d %H-%M-%S'):
        if dt is None: dt = datetime.now()
        return dt.strftime(strformat)

    ## Converts a string to a Python `datetime` object.
    # See utils::str_to_datetime()
    def _str_to_datetime(self, text, strformat='%Y-%m-%d %H-%M-%S'):
        return datetime.strptime(text, strformat)

    ## Initializes Updater::update_info from the update.log file or creates that file.
    def _init_update_info(self):
        if self.update_file.exists():
             with open(str(self.update_file), 'r', encoding=ENCODING) as infile:
                self.update_info.update(json.load(infile))
        else:
            self._write_update_info()

    ## Writes the update info from Updater::update_info to the update.log file.
    def _write_update_info(self):
        with open(str(self.update_file), 'w', encoding=ENCODING) as outfile:
            json.dump(self.update_info, outfile, ensure_ascii=False, indent='\t')

    ## Strips unacceptable characters from a version string.
    # @param version_str `str` the version string to sanitize
    # @returns `str` sanitized version string (containing only numbers and dots)
    def _strip_version_az(self, version_str):
        return ''.join([c for c in version_str if c in list('0123456789.')])

    ## Converts a version string into a tuple of version numbers.
    # @param version_str `str` the version string to convert
    # @param max_versions `int` max version depth to convert.
    # For example, if `version_str` == '3.0.1.2' and `max_versions` == 2,
    # the resulting tuple will be `(3, 0)` -- only 2 version sections.
    # The value of -1 (default) lifts this limitation.
    # @returns `tuple` | `None` tuple containing the version sections in their
    # original order, e.g. '3.0.1.2' -> `(3, 0, 1, 2)`; `None` on
    # failure (incorrect input version string)
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

    ## Compares two version strings and checks if one is later than the other.
    # @param v1 `str` the first (left) version string
    # @param v2 `str` the second (right) version string
    # @param max_versions `int` max version depth to parse (see _parse_version())
    # @param major_only `bool` compare only major versions (first version
    # number in each version string)
    # @returns `str` comparison result:
    #   * '>' if `v1` is **later** than `v2`
    #   * '<' if `v1` is **older** than `v2`
    #   * '=' if `v1` is **the same** as `v2`
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



