# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

import requests, os, uuid
import urllib.parse
from abc import ABC, abstractmethod
from .globalvars import (MW_DIC_KEY, MW_DIC_HTTP, MW_WORD_URL, 
                        YAN_DICT_KEY, YAN_DICT_HTTP,
                        SHAREAHOLIC_KEY, SHAREAHOLIC_HTTP,
                        GOOGLE_KEY, GOOGLE_CSE, GOOGLE_HTTP, GOOGLE_LANG_LR, 
                        GOOGLE_LANG_HL, GOOGLE_COUNTRIES_CR, GOOGLE_COUNTRIES_GL)
from .utils import MsgBox                 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class GoogleSearch:

    def __init__(self, settings, search_phrase='', exact_match=False, file_types=None, lang=None,
                 country=None, interface_lang=None, link_site=None, related_site=None, in_site=None, 
                 nresults=-1, safe_search=False, timeout=5000):
        self.settings = settings
        self.init(search_phrase, exact_match, file_types, lang, country, interface_lang, link_site,
                  related_site, in_site, nresults, safe_search, timeout)

    def init(self, search_phrase='', exact_match=False, file_types=None, lang=None,
                 country=None, interface_lang=None, link_site=None, related_site=None, in_site=None, 
                 nresults=-1, safe_search=False, timeout=5000):
        self.search_phrase = search_phrase
        self.exact_match = exact_match
        self.file_types = file_types
        self.lang = lang
        self.country = country
        self.interface_lang = interface_lang
        self.link_site = link_site
        self.related_site = related_site
        self.in_site = in_site
        self.nresults = nresults if nresults < 10 else 10
        self.safe_search = safe_search
        self.timeout = timeout

    def encode_search(self):
        url = GOOGLE_HTTP.format(self.settings['lookup']['google']['api_key'] or GOOGLE_KEY,
                                 self.settings['lookup']['google']['api_cse'] or GOOGLE_CSE,
                                 urllib.parse.quote(self.search_phrase))
        if self.exact_match:
            url += f"&exactTerms={urllib.parse.quote(self.search_phrase)}"
        if self.file_types:
            url += f"&fileType={','.join(self.file_types) if isinstance(self.file_types, list) or isinstance(self.file_types, tuple) else self.file_types}"
        if self.lang:
            url += f"&lr={'|'.join([('lang_' + l.lower()) for l in self.lang]) if isinstance(self.lang, list) or isinstance(self.lang, tuple) else ('lang_' + self.lang.lower())}"
        if self.country:
            url += f"&gl={'|'.join(self.country) if isinstance(self.country, list) or isinstance(self.country, tuple) else self.country}"
        if self.interface_lang:
            url += f"&hl={'|'.join(self.interface_lang) if isinstance(self.interface_lang, list) or isinstance(self.interface_lang, tuple) else self.interface_lang}"
        if self.link_site:
            url += f"&linkSite={self.link_site}"
        if self.related_site:
            url += f"&relatedSite={self.related_site}"
        if self.in_site:
            url += f"&siteSearch={self.in_site}"
        if self.nresults > 0:
            url += f"&num={self.nresults}"
        if self.safe_search:
            url += f"&safe=active"
        return url

    def decode_result(self, txt):
        return urllib.parse.unquote(txt)

    def search(self, method='json'):
        """
        Returns full Google search results for 'self.search_phrase'.
        """
        res = requests.get(self.encode_search(), timeout=self.timeout)
        if res:
            res = res.json() if method == 'json' else res.content
            if isinstance(res, dict) and 'error' in res:
                raise Exception(f"Request returned error '{res.get('message', 'Invalid request')}', code = {res.get('code', 400)}")
            return res
        else:
            raise Exception(f"Request returned error {res.status_code}")

    def search_lite(self):
        """
        Retrieves search results for 'self.search_phrase' as a list in the following format:
        [{'url': 'URL', 'title': 'TITLE', 'summary': 'SNIPPET'}, ...]
        See https://developers.google.com/custom-search/v1/cse/list
        """
        res = self.search()
        if not res: return None
        # if we are here, it means no exceptions have occurred...
        return [{'url': item['link'], 'title': item['title'], 'summary': item['snippet']} for item in res['items']]

    @staticmethod
    def get_interface_languages():
        return GOOGLE_LANG_HL

    @staticmethod
    def get_document_languages():
        return GOOGLE_LANG_LR

    @staticmethod
    def get_document_countries():
        return GOOGLE_COUNTRIES_CR

    @staticmethod
    def get_user_countries():
        return GOOGLE_COUNTRIES_GL
        
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class OnlineDictionary(ABC):

    def __init__(self, settings, url_template='', timeout=5000):
        self.url = url_template
        self.timeout = timeout
        self.settings = settings

    def prepare_request_url(self, word):
        return self.url.format(word)

    def get_definitions(self, word, method='json'):
        """
        Returns full definitions for 'word' in JSON (python object) or raw text format.
        """
        res = requests.get(self.prepare_request_url(word), timeout=self.timeout)
        if res:
            return res.json() if method == 'json' else res.content
        else:
            raise Exception(f"Request returned error {res.status_code}")

    @abstractmethod
    def get_short_defs(self, word, exact_match=True, partsofspeech=None, bad_pos='UNKNOWN'):
        """
        Returns the abridged definition for the given entry.
        Params:
        - word [str]: the word query
        - exact_match [bool]: if True, only defitions for the exact word given by 'word' will be returned
        - partsofspeech [list or tuple]: parts of speech to get definitions for
        (None = all available)
        - bad_pos [str]: substitution for part of speech if unavailable        
        Returns:
        - list of short definitions in the format:
        [('word', 'part of speech', [list of defs], 'url'), ...]
        """
        return []

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class MWDict(OnlineDictionary):

    def __init__(self, settings, timeout=5000):
        super().__init__(settings, MW_DIC_HTTP, timeout)

    def prepare_request_url(self, word):
        return self.url.format(word, self.settings['lookup']['dics']['mw_apikey'] or MW_DIC_KEY)

    def get_short_defs(self, word, exact_match=True, partsofspeech=None, bad_pos='UNKNOWN'):
        entry = self.get_definitions(word)
        if not entry or not isinstance(entry, list): return None
        results = []
        for hom in entry:
            if not isinstance(hom, dict): continue
            wd = hom.get('hwi', None)            
            if not wd or not isinstance(wd, dict): continue
            wd = wd.get('hw', None)
            if not wd: continue
            wd = wd.replace('*', '')
            if exact_match and wd.lower() != word.lower(): continue
            pos = hom.get('fl', bad_pos)            
            if (not partsofspeech) or (pos in partsofspeech):
                defs = hom.get('shortdef', None)
                results.append((wd, pos, defs, MW_WORD_URL.format(urllib.parse.quote_plus(wd))))
        return results

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class YandexDict(OnlineDictionary):

    def __init__(self, settings, lang='ru-ru', timeout=5000):
        self.lang = lang
        super().__init__(settings, YAN_DICT_HTTP, timeout)

    def prepare_request_url(self, word):
        return self.url.format(self.settings['lookup']['dics']['yandex_key'] or YAN_DICT_KEY, 
                                word, self.lang)

    def get_short_defs(self, word, exact_match=True, partsofspeech=None, bad_pos='UNKNOWN'):
        entry = self.get_definitions(word)
        if not entry or not isinstance(entry, dict): return None
        defs = entry.get('def', [])
        results = []
        for hom in defs:
            try:
                wd = hom['text']
                if exact_match and wd.lower() != word.lower(): continue
                pos = hom.get('pos', bad_pos)
                if (not partsofspeech) or (pos in partsofspeech):
                    wdefs = []
                    for tr in hom['tr']:
                        wdefs.append(tr['text'])
                        syns = tr.get('syn', [])
                        for syn in syns:
                            wdefs.append(syn['text'])                
                    results.append((wd, pos, wdefs, ''))
            except Exception as err: 
                print(err)
                continue
        return results

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class Cloudstorage:

    ACCID = 352604900
    BEARER = 'weov2heMt4VYnhi78egvYYV55qoa9S'
    ROOTNAME = 'pycrossall'
    ROOTID = 'Fn6Cw1UD_PxkjIc8EN8u0uJHm4FsKBp6RCIGrNq6R9KQ='

    def __init__(self, settings):
        self.settings = settings
        self.users = []
        self.init_settings()        

    def init_settings(self):        
        self._accid = self.settings['account'] or Cloudstorage.ACCID
        self._baseurl = f"https://api.kloudless.com/v2/accounts/{self._accid}/storage/"
        self._bearer = self.settings['bearer_token'] or Cloudstorage.BEARER
        self._headers = {'Content-Type': 'application/json', 'Authorization': f"Bearer {self._bearer}"}
        self._rootid = ''
        rootname = self.settings['root_folder'] \
            if (self.settings['root_folder'] and self.settings['account'] \
                and self.settings['bearer_token']) else Cloudstorage.ROOTNAME
        new_folder = self._create_folder(rootname)
        if new_folder:
            self._rootid = new_folder[1]                  
            self.settings['root_folder'] = '' if new_folder[0] == Cloudstorage.ROOTNAME else new_folder[0]
        else:
            MsgBox(f"Unable to create/access folder '{rootname}'!", 
                    title='Error', msgtype='error')    

        self.find_or_create_user(self.settings['user'])

    def _create_account(self):
        """
        Create a new client account and bind it to the Kloudless/pycross app.
        Retrieved Account ID and Bearer Token will be written to settings.
        TODO: Implement when default Dropbox storage is not enough.
        """
        return

    def _get_quota(self):
        """
        Retrieves storage quota information.
        """
        req = f"{self._baseurl}quota"
        try:
            res = requests.get(req, headers=self._headers)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return res.json() if res else None

    def _get_folder_objects(self, fid, recurse=False):
        if not fid:
            MsgBox('Empty folder ID passed to _get_folder_objects()!', title='Error', msgtype='error')
            return None
        req = f"{self._baseurl}folders/{urllib.parse.quote(fid)}/contents/?recursive={str(recurse).lower()}"
        res = None
        try:
            res = requests.get(req, headers=self._headers)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return res.json() if res else None

    def _generate_username(self):
        while True:
            usr = uuid.uuid4().hex
            for u in self.users:
                if u[0] == usr:
                    break
            else:
                return usr

    def _create_folder(self, folder_name, parent_id='root', error_on_exist=False):
        folder_name = folder_name.lower()
        data = {'parent_id': urllib.parse.quote(parent_id), 'name': urllib.parse.quote(folder_name)}
        req = f"{self._baseurl}folders/?conflict_if_exists={str(error_on_exist).lower()}"
        print(self._headers)
        print(req)
        res = None
        try:
            res = requests.post(req, headers=self._headers, data=data)
        except requests.exceptions.RequestException as e:
            if res.status_code == 409:
                MsgBox(f"Folder '{folder_name}' already exists!", 
                      title='HTTP(S) request error', msgtype='warn')
                return None
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        if not res: return None
        res = res.json()
        print(res)
        return (res['name'], res['id'])

    def _update_users(self):
        """
        Updates the list of subfolders present in dropbox/pycrossall root folder.
        The names of these subfolders correspond to the names of the
        registered users.
        """        
        res = self._get_folder_objects(self._rootid)        
        self.users = []
        if not res: return
        for obj in res['objects']:
            if obj['type'] != 'folder': continue
            self.users.append((obj['name'].lower(), obj['id']))

    def _get_file_metadata(self, file_id):
        """
        Retrieves the metadata of the given file: name, path, size, date, etc.
        """
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/"
        try:
            res = requests.get(req, headers=self._headers)
            if not res: return None
            return res.json()
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return None

    def _get_folder_metadata(self, folder_id=None):
        """
        Retrieves the metadata of the given folder: name, path, size, date, etc.
        If 'folder_id' is None, the current user's folder will be used.
        """
        if not folder_id: 
            if not self._user:
                MsgBox('Neither the folder ID not the user ID is valid!', title='HTTP(S) request error', msgtype='error')
                return None
            folder_id = self._user[1]
        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/"
        try:
            res = requests.get(req, headers=self._headers)
            if not res: return None
            return res.json()
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return None

    def find_or_create_user(self, username=None, error_on_exist=False):
        """
        Creates or finds the subfolder: dropbox/pycrossall/<username>.
        If found and 'error_on_exist' == True, displays error and quits.
        Otherwise, sets self._user = (user_name, user_id).
        On any failure, self._user will be set to None.
        If username == None (default), an automatic username is generated.
        """
        self._user = None       
        self._update_users()
        if username:
            username = username.lower()
            for u in self.users:
                if u[0] == username:
                    if error_on_exist:
                        MsgBox(f"Username '{username}' is already occupied! Please choose another.", 
                            title='HTTP(S) request error', msgtype='warn')                    
                    else:
                        self._user = u
                    self.settings['user'] = username
                    return
        else:
            username = self._generate_username()
        new_user = self._create_folder(username, self._rootid)
        if new_user:
            self.users.append(new_user)
            self._user = new_user
            self.settings['user'] = username
        else:
            self.settings['user'] = ''

    def find_or_create_folder(self, folder_name):
        """
        Finds or creates new subfolder in user's folder.
        Returns the tuple (folder_name, folder_id) or None on failure.
        """
        return self._create_folder(folder_name, self._user[1], False)

    def clear_folder(self, folder_id=None):
        """
        Clears given (sub)folder.
        """
        if not folder_id: 
            if not self._user:
                MsgBox('Neither the folder ID not the user ID is valid!', title='HTTP(S) request error', msgtype='error')
                return None
            folder_id = self._user[1]
        # get folder name
        folder_info = self._get_folder_metadata(folder_id)
        if not folder_info: return None
        folder_name = folder_info.get('name', None)
        if not folder_name: return None
        folder_parent = folder_info.get('parent', None)
        if not folder_parent: return None
        folder_parent = folder_parent['id']
        # delete folder
        if not self.delete_folder(folder_id): return None
        # recreate folder
        res = self._create_folder(folder_name, folder_parent, True)
        if folder_id == self._user[1]:
            # update user info
            self._user = res
            self.settings['user'] = res[0] if res else ''
        return res

    def delete_folder(self, folder_id, permanent=True, recurse=True):
        """
        Deletes the folder with the given ID, optionally permanently.
        Returns True on success, False otherwise.
        """
        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/?permanent={str(permanent).lower()}&recursive={str(recurse).lower()}"
        headers = self._headers.copy()
        headers['Content-Type'] = 'application/octet-stream'
        try:
            res = requests.delete(req, headers=headers)
            return bool(res)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return False
        return False

    def rename_folder(self, folder_id, new_name):
        """
        Renames the given (sub)folder to 'new_name'.
        Returns the tuple (folder_name, folder_id) or None on failure.
        """
        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/"
        data = {'name': urllib.parse.quote(new_name)}
        try:
            res = requests.patch(req, headers=self._headers, data=data)
            if not res: return None
            res = res.json()
            return (res['name'], res['id'])
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return None
        
    def upload_file(self, filepath, folder_id=None, overwrite=False, 
                    makelink=True, activelink=True, 
                    directlink=True, expire=None, password=None):
        """
        Uploads a file into the current user's folder (optionally subfolder) and returns the link info.
        If 'overwrite' == True, the first file with the same name will be overwritten.
        Otherwise, the uploaded file will be automatically renamed.
        """
        if getattr(self, '_user', None) is None:
            MsgBox('Current user is not defined! Please create new user first.', title='Error', msgtype='error')
            return None
        if not os.path.isfile(filepath):
            MsgBox(f"File '{filepath}' is not accessable!", title='Error', msgtype='error')
            return None

        # get file size (bytes)
        fsize = os.path.getsize(filepath)
        
        # upload file
        headers = self._headers.copy()
        headers['Content-Type'] = 'application/octet-stream'
        headers['X-Kloudless-Metadata'] = {'name': os.path.basename(filepath), 
            'parent_id': urllib.parse.quote(self._user[1] if not folder_id else folder_id)}
        headers['Content-Length'] = fsize
        req = f"{self._baseurl}files/?overwrite={str(overwrite).lower()}"

        res = None
        with open(filepath, 'rb') as f:            
            try:
                res = requests.post(req, headers=headers, data=f)
            except requests.exceptions.RequestException as e:
                MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
                return None

        if not res: return None
        res = res.json()
        return self.create_file_link(res['id'], activelink, directlink, expire, password) \
               if makelink else res

    def delete_file(self, file_id, permanent=True):
        """
        Deletes the file with the given ID, optionally permanently.
        Returns True on success, False otherwise.
        """
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/?permanent={str(permanent).lower()}"
        headers = self._headers.copy()
        headers['Content-Type'] = 'application/octet-stream'
        try:
            res = requests.delete(req, headers=headers)
            return bool(res)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return False
        return False

    def rename_file(self, file_id, new_name):
        """
        Renames the given file (in the original folder).
        Returns the tuple (file_name, file_id) or None on failure.
        """
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/"
        data = {'name': urllib.parse.quote(new_name)}
        try:
            res = requests.patch(req, headers=self._headers, data=data)
            if not res: return None
            res = res.json()
            return (res['name'], res['id'])
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return None

    def download_file(self, file_id, save_folder='', overwrite=False):
        """
        Downloads the given file to the folder given by 'save_folder'.
        If 'save_folder' is empty, the file is downloaded to the working dir.
        Returns True on success / False otherwise.
        """
        file_info = self._get_file_metadata(file_id)
        if not save_folder:
            save_folder = os.getcwd()
        filepath = os.path.join(os.path.abspath(save_folder), file_info['name'] if file_info else 'UNKNOWN_FILE')
        if not overwrite and os.path.isfile(filepath):
            MsgBox(f"File '{filepath}' already exists!", title='HTTP(S) request error', msgtype='warn')
            return False

        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/contents/"
        headers = self._headers.copy()
        headers['Content-Type'] = file_info['mime_type'] if file_info else 'application/octet-stream'
        try:
            res = requests.get(req, headers=headers, allow_redirects=True)
            if not res: return False
            with open(filepath, 'wb') as fout:
                fout.write(res.content)
            return bool(res)
        except Exception as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return False

        return False

    def create_file_link(self, file_id, activelink=True, directlink=True, 
                         expire=None, password=None):
        """
        Creates public link to specified file (given by file ID).
        Returns the link meta info (dict).
        """
        if not file_id:
            MsgBox('Empty file ID passed to create_file_link()!', title='Error', msgtype='error')
            return None

        req = f"{self._baseurl}links/"
        data = {'file_id': urllib.parse.quote(file_id), 'direct': directlink, 'active': activelink}
        if not expire is None:
            data['expiration'] = expire.isoformat()
        if not password is None:
            data['password'] = urllib.parse.quote(password)
        res = None
        try:
            res = requests.post(req, headers=self._headers, data=data)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return res.json() if res else None

    def get_file_link(self, link_id):
        """
        Retrieves file link info (given by link ID).
        Returns the link meta info (dict).
        """
        if not link_id:
            MsgBox('Empty link ID passed to get_file_link()!', title='Error', msgtype='error')
            return None
        req = f"{self._baseurl}links/{urllib.parse.quote(link_id)}/"
        res = None
        try:
            res = requests.get(req, headers=self._headers)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return res.json() if res else None

    def update_file_link(self, link_id, activelink=None,  
                         expire=None, password=None):
        """
        Updates public link to specified file (given by file ID).
        Returns the link meta info (dict).
        """
        if not link_id:
            MsgBox('Empty link ID passed to update_file_link()!', title='Error', msgtype='error')
            return None

        req = f"{self._baseurl}links/{urllib.parse.quote(link_id)}/"
        data = {}
        if not activelink is None:
            data['active'] = bool(activelink)
        if not expire is None:
            data['expiration'] = expire.isoformat()
        if not password is None:
            data['password'] = urllib.parse.quote(password)
        res = None
        try:
            res = requests.patch(req, headers=self._headers, data=data)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return None
        return res.json() if res else None

    def delete_file_link(self, link_id):
        """
        Deletes public link to specified file (given by file ID).
        Returns True on success / False on failure.
        """
        if not link_id:
            MsgBox('Empty link ID passed to delete_file_link()!', title='Error', msgtype='error')
            return None

        req = f"{self._baseurl}links/{urllib.parse.quote(link_id)}/"       
        res = None
        try:
            res = requests.delete(req, headers=self._headers)
            return bool(res)
        except requests.exceptions.RequestException as e:
            MsgBox(str(e), title='HTTP(S) request error', msgtype='error')
            return False
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class Share:

    def __init__(self, settings, url=SHAREAHOLIC_HTTP, timeout=5000):
        self.settings = settings
        self.url = url
        self.timeout = timeout

    def prepare_request_url(self, *args):
        return self.url.format(SHAREAHOLIC_KEY, *args)

    def share(self, filepath, upload_to='gdrive', social='twitter', 
              title='My new crossword', notes='See my new crossword',
              url_shortener='google', tags=''):
        pass

