# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from .globalvars import (APP_VERSION, GIT_REPO, ENCODING, UPDATE_FILE)
from .utils import *
from datetime import datetime
import os, subprocess, json

# git fetch -q git reset --hard -q <VERSION>

class Updater:

    def __init__(self, update_settings, quit_app_method, 
                 on_get_recent=None, on_before_update=None):
        self.update_settings = update_settings
        self.quit_app_method = quit_app_method
        self.on_get_recent = on_get_recent
        self.on_before_update = on_before_update
        self.git_installed = self._check_git()        
        self._init_update_info()

    def __del__(self):
        self._write_update_info()

    def _init_update_info(self):
        if os.path.isfile(UPDATE_FILE):
             with open(os.path.abspath(UPDATE_FILE), 'r', encoding=ENCODING, errors='replace') as infile:
                self.update_info = json.load(infile)                
        else:
            self.update_info = {'last_update': '', 'last_check': '', 
                                'recent_version': {'version': '', 'description': '', 'date': ''}}
            
    def _write_update_info(self):
        with open(os.path.abspath(UPDATE_FILE), 'w', encoding=ENCODING) as outfile:
            json.dump(self.update_info, outfile, ensure_ascii=False, indent='\t')

    def _parse_version(self, version_str, max_versions=2):
        version_str = ''.join([c for c in version_str if c in list('0123456789.')])
        print(version_str.split('.'))
        return tuple([int(v) for v in version_str.split('.')][:max_versions])

    def _compare_versions(self, v1, v2, major_only=False):
        tv1 = self._parse_version(v1)
        tv2 = self._parse_version(v2)        
        l = min(len(tv1), len(tv2))
        tv1 = tv1[:l] 
        tv2 = tv2[:l] 
        if l == 0: return '='
        if major_only: l = 1
        for i in range(l):
            if tv1[i] < tv2[i]: return '<'
            if tv1[i] > tv2[i]: return '>'
        return '='

    def _check_git(self):
        res = run_exe(['git', '--version'])
        return res.returncode == 0

    def _get_recent_version(self):
        if not self.git_installed:
            return {'error': 'You do not appear to have a valid version of git installed!\nPlease install git from https://git-scm.com/'}
        res = run_exe(os.path.abspath('git_get_recent.bat'))
        if res.returncode != 0:
            return {'error': res.stderr}
        rec_vers = res.stdout.strip()
        if not rec_vers:
            return {'error': 'No version tags found in remote repository!'}
        res = run_exe(['git', 'tag', '--list', rec_vers, '-n99'])
        tag_descr = res.stdout.strip()
        if tag_descr: tag_descr = tag_descr[len(rec_vers):]
        return {'version': rec_vers, 'description': tag_descr}

    def _reset_to_version(self, version_str):
        if not version_str or not self.git_installed: return None
        return run_exe([os.path.abspath('git_reset_to_version.bat'), version_str], True)

    def _update_check_required(self):
        dt_now = datetime.now()
        dt_lastcheck = str_to_datetime(self.update_info['last_check']) if self.update_info['last_check'] else None
        return dt_lastcheck is None or \
            (self.update_settings['check_every'] > 0 and \
            (dt_now - dt_lastcheck).days >= self.update_settings['check_every'])

    def check_update(self, force=False):
        if not force and not self._update_check_required():
            return None
        recent_vers = self._get_recent_version()
        if self.on_get_recent and not self.on_get_recent(recent_vers):
            return None
        if 'error' in recent_vers:
            print(recent_vers['error'])
            return None
        res = None
        if self._compare_versions(APP_VERSION, recent_vers['version'], 
                                 self.update_settings['only_major_versions']) == '<':
            res = recent_vers
        self.update_info['last_check'] = datetime_to_str()
        self.update_info['recent_version'] = res or ''
        self._write_update_info()
        return res    

    def update(self, force=False):
        vers = self.check_update(force)
        if not vers: return
        if self.on_before_update and not self.on_before_update(vers): 
            return
        self.update_info['last_update'] = datetime_to_str()
        self._write_update_info()
        if not self._reset_to_version(vers['version']) is None:
            self.quit_app_method()

    

    




