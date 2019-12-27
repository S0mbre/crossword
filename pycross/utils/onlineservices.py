# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

import requests, os, uuid, json, webbrowser
import urllib.parse
from abc import ABC, abstractmethod
from .globalvars import (MW_DIC_KEY, MW_DIC_HTTP, MW_WORD_URL, 
                        YAN_DICT_KEY, YAN_DICT_HTTP,
                        GOOGLE_KEY, GOOGLE_CSE, GOOGLE_HTTP, GOOGLE_LANG_LR, 
                        GOOGLE_LANG_HL, GOOGLE_COUNTRIES_CR, GOOGLE_COUNTRIES_GL)
from .utils import MsgBox, UserInput, clipboard_copy                 

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

    APIURL = 'https://api.kloudless.com/v2/'
    ACCID = 352604900 # dropbox account ID (connected to the pycross app on Kloudless)
    ROOTNAME = 'pycrossall'
    #ROOTID = 'Fn6Cw1UD_PxkjIc8EN8u0uF4LYc2hdbgF8VEy6eS7eyg='

    def __init__(self, settings, timeout=5000):
        self.settings = settings
        self.timeout = timeout
        self.users = []
        self.init_settings()        

    def init_settings(self):        
        self._accid = self.settings['account'] or Cloudstorage.ACCID
        self._baseurl = f"{Cloudstorage.APIURL}accounts/{self._accid}/storage/"
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

        self._find_or_create_user(self.settings['user'])

    def _request(self, url, command='get', returntype='json',  
                 show_errors=True, on_error=None, error_keymap={'message': 'message', 'code': 'status_code'},
                 **kwargs):

        methods = {'get': requests.get, 'post': requests.post, 'delete': requests.delete,
                   'patch': requests.patch}  
        res = None      
        try:
            kwargs['timeout'] = kwargs.get('timeout', self.timeout)
            res = methods[command](url, **kwargs)
            if res is None: raise Exception(f"Empty result returned by request '{url}'")
            if not res:
                try:
                    err = res.json()
                except:
                    err = {}
                err = {'message': str(err.get(error_keymap['message'], f"Error returned by request '{url}'")),
                       'code': err.get(error_keymap['code'], None)}                  
                if on_error: on_error(err)
                if show_errors:
                    MsgBox(err['message'], 
                           title=f"Error{' ' + str(err['code']) if err['code'] else ''}", 
                           msgtype='error')
                return None if returntype != 'bool' else False

        except Exception as e:
            if show_errors: MsgBox(str(e), title='Error', msgtype='error')
            return None if returntype != 'bool' else False

        if returntype == 'bool': return True
        if returntype == 'json': return res.json()
        if returntype == 'text': return res.text
        return res.content

    def _get_apikey(self):
        if not getattr(self, '_apikey', None):
            res = UserInput(label='Enter your API key', textmode='password')
            self._apikey = res[0] if res[1] else None

    def _get_bearer(self):
        self._bearer = self.settings.get('bearer_token', None)
        if not self._bearer:
            res = UserInput(label='Enter your Bearer token', textmode='password')
            self._bearer = res[0] if res[1] else None
            self.settings['bearer_token'] = self._bearer or ''

    def _make_headers(self, content_type='application/json', force_api_key=False):
        auth = None
        if self.settings['use_api_key'] or force_api_key:
            self._get_apikey()
            if not self._apikey:
                raise Exception('No valid API key provided!\nProvide a valid API key or change your "use_api_key" settings\nto use a different authentication method.')
            auth = f"APIKey {self._apikey}"
        else:
            self._get_bearer()
            if not self._bearer:
                raise Exception('No valid Bearer token provided!\nProvide a valid Bearer token or change your "use_api_key" settings\nto use a different authentication method.')
            auth = f"Bearer {self._bearer}"
        return {'Content-Type': content_type, 'Authorization': auth}

    def _create_account(self):
        """
        Create a new client account and bind it to the Kloudless/pycross app.
        Retrieved Account ID and Bearer Token will be written to settings.
        TODO: Implement when default Dropbox storage is not enough.
        """
        return

    def _get_accounts(self, enabled=None, admin=None, search=None):
        """
        Service method: lists all accounts tied to the pycross app on Kloudless.
        """
        req = f"{Cloudstorage.APIURL}accounts/" 
        if not enabled is None:
            req += f"?enabled={str(enabled).lower()}"
        if not admin is None:
            req += '?' if req.endswith('/') else '&'
            req += f"admin={str(admin).lower()}"
        if not search is None:
            req += '?' if req.endswith('/') else '&'
            req += f"search={urllib.parse.quote_plus(search)}"

        return self._request(req, headers=self._make_headers(force_api_key=True))

    def _get_account_matadata(self, account_id, retrieve_tokens=False, retrieve_full=True):
        """
        Service method: gets metadata for account specified by 'account_id'.
        """
        req = f"{Cloudstorage.APIURL}accounts/{account_id}/?retrieve_tokens={str(retrieve_tokens).lower()}&retrieve_full={str(retrieve_full).lower()}" 
        return self._request(req, headers=self._make_headers(force_api_key=True))

    def _get_quota(self):
        """
        Retrieves storage quota information.
        """
        req = f"{self._baseurl}quota"
        return self._request(req, headers=self._make_headers())

    def _get_folder_objects(self, fid, recurse=False):
        if not fid:
            MsgBox('Empty folder ID passed to _get_folder_objects()!', title='Error', msgtype='error')
            return None
        req = f"{self._baseurl}folders/{urllib.parse.quote(fid)}/contents/?recursive={str(recurse).lower()}"
        return self._request(req, headers=self._make_headers())

    def _get_folder_ancestors(self, folder_id):
        folder_info = self._get_folder_metadata(folder_id)
        if not folder_info: return None
        return folder_info.get('ancestors', None)

    def _is_user_folder(self, folder_id):
        """
        Checks if given folder is inside current user's folder.
        """
        if not self._user: return False
        ancestors = self._get_folder_ancestors(folder_id)
        if not ancestors: return False
        for anc in ancestors:
            index = 2 if anc['id_type'] == 'path' else 1
            if anc['id'] == self._user[index]:
                return True
        return False

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
        data = {'parent_id': parent_id, 'name': folder_name}
        req = f"{self._baseurl}folders/?conflict_if_exists={str(error_on_exist).lower()}"
        res = self._request(req, 'post', headers=self._make_headers(), json=data)        
        return (res['name'], res['id'], res['ids']['path']) if res else None

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
            self.users.append((obj['name'].lower(), obj['id'], obj['ids']['path']))

    def _get_file_metadata(self, file_id):
        """
        Retrieves the metadata of the given file: name, path, size, date, etc.
        """
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/"
        return self._request(req, headers=self._make_headers())

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
        return self._request(req, headers=self._make_headers())

    def _find_or_create_user(self, username=None, error_on_exist=False):
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

    def _delete_user(self, username=None):
        if username and self._user and username != self._user[0]:            
            self._get_apikey()
            if not self._apikey:
                MsgBox('You can delete other users only with a valid API key!', 
                       title='Error', msgtype='error')
                return False
            user_folder = self._create_folder(username, self._rootid)   
            return self.delete_folder(user_folder[1]) if user_folder else False
        elif self._user:
            return self.delete_folder(self._user[1])
        MsgBox('No current user present!', title='Error', msgtype='error')
        return False

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
                return False
            folder_id = self._user[1]
        elif not self._is_user_folder(folder_id):
            # check if folder is in current user's folder
            self._get_apikey()
            if not self._apikey:
                MsgBox('You cannot clear folders created by other users without a valid API key!', 
                    title='Error', msgtype='error')
                return False

        # get folder object
        res = self._get_folder_objects(folder_id, False)
        if not res or not res['objects']: return True
        results = []
        # iterate for onjects in folder
        for obj in res['objects']:
            req = ''
            if obj['type'] != 'folder': 
                req = f"{self._baseurl}folders/{urllib.parse.quote(obj['id'])}/?permanent=true&recursive=true"
            elif obj['type'] != 'file': 
                req = f"{self._baseurl}files/{urllib.parse.quote(obj['id'])}/?permanent=true"
            if req:
                try:
                    res = requests.delete(req, headers=self._make_headers('application/octet-stream'))
                    results.append(bool(res))
                except Exception:
                    results.append(False)

        return all(results)

    def delete_folder(self, folder_id, permanent=True, recurse=True):
        """
        Deletes the folder with the given ID, optionally permanently.
        Returns True on success, False otherwise.
        """
        if not folder_id:
            MsgBox('No folder ID provided', title='Error', msgtype='error')
            return False

        # check if folder is in current user's folder
        if not self._is_user_folder(folder_id):
            self._get_apikey()
            if not self._apikey:
                MsgBox('You cannot clear folders created by other users without a valid API key!', 
                    title='Error', msgtype='error')
                return False

        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/?permanent={str(permanent).lower()}&recursive={str(recurse).lower()}"
        return self._request(req, 'delete', 'bool', headers=self._make_headers('application/octet-stream'))
        
    def rename_folder(self, folder_id, new_name):
        """
        Renames the given (sub)folder to 'new_name'.
        Returns the tuple (folder_name, folder_id) or None on failure.
        """
        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/"
        data = {'name': new_name}
        res = self._request(req, 'patch', headers=self._make_headers(), json=data)
        return (res['name'], res['id'], res['ids']['path']) if res else None
        
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
        headers = self._make_headers('application/octet-stream')
        headers['X-Kloudless-Metadata'] = json.dumps({'name': os.path.basename(filepath), 
            'parent_id': self._user[1] if not folder_id else folder_id})
        headers['Content-Length'] = str(fsize)
        req = f"{self._baseurl}files/?overwrite={str(overwrite).lower()}"

        res = None
        with open(filepath, 'rb') as f:      
            res = self._request(req, 'post', headers=headers, data=f)     
        if not res: return None
        return self.create_file_link(res['id'], activelink, directlink, expire, password) \
               if makelink else res

    def delete_file(self, file_id, permanent=True):
        """
        Deletes the file with the given ID, optionally permanently.
        Returns True on success, False otherwise.
        """
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/?permanent={str(permanent).lower()}"
        return self._request(req, 'delete', 'bool', headers=self._make_headers('application/octet-stream'))

    def rename_file(self, file_id, new_name):
        """
        Renames the given file (in the original folder).
        Returns the tuple (file_name, file_id) or None on failure.
        """
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/"
        data = {'name': new_name}
        res = self._request(req, 'patch', headers=self._make_headers(), json=data)
        return (res['name'], res['id'], res['ids']['path']) if res else None

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
        res = self._request(req, returntype='content', 
                            headers=self._make_headers(file_info['mime_type'] if file_info \
                            else 'application/octet-stream'), allow_redirects=True)
        if not res: return False
        with open(filepath, 'wb') as fout:
            fout.write(res)
        return True

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
        data = {'file_id': file_id, 'direct': directlink, 'active': activelink}
        if not expire is None:
            data['expiration'] = expire.isoformat()
        if not password is None:
            data['password'] = password
        return self._request(req, 'post', headers=self._make_headers(), json=data)

    def get_file_link(self, link_id):
        """
        Retrieves file link info (given by link ID).
        Returns the link meta info (dict).
        """
        if not link_id:
            MsgBox('Empty link ID passed to get_file_link()!', title='Error', msgtype='error')
            return None
        req = f"{self._baseurl}links/{urllib.parse.quote(link_id)}/"
        return self._request(req, headers=self._make_headers())

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
            data['password'] = password
        return self._request(req, 'patch', headers=self._make_headers(), json=data)

    def delete_file_link(self, link_id):
        """
        Deletes public link to specified file (given by file ID).
        Returns True on success / False on failure.
        """
        if not link_id:
            MsgBox('Empty link ID passed to delete_file_link()!', title='Error', msgtype='error')
            return None

        req = f"{self._baseurl}links/{urllib.parse.quote(link_id)}/"       
        return self._request(req, 'delete', 'bool', headers=self._make_headers())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class Share:

    APPID = 'abf1b67f10817416ba9fee9b76455bef'
    BASEURL = 'https://www.shareaholic.com/api/share/?v=1&apitype=1'
    ERRMAP = {'message': 'data', 'code': 'code'}
    SERVICES = {'twitter': 7, 'facebook': 5, 'pinterest': 309, 'linkedin': 88, 'gmail': 52,
                'yahoomail': 54, 'aolmail': 55, 'hotmail': 53, 'myspace': 39,
                'reddit': 40, 'skype': 989, 'tumblr': 78, 'yandex': 267, 'clipboard': 0}

    def __init__(self, cloud: Cloudstorage, settings, timeout=5000):
        self.settings = settings
        self.timeout = timeout
        if not cloud:
            raise Exception('Share object must be given a valid instance of Cloudstorage as the "cloud" argument!')
        self.cloud = cloud
        # dirty hack for convenience
        self._request = self.cloud._request

    def share(self, file_or_url, social='twitter', 
              title='My new crossword', notes='See my new crossword',
              url_shortener='google', tags='pycross,crossword,python',
              source='pyCross'):
        serv = social
        just_copy_url = False
        if isinstance(serv, str):
            serv = Share.SERVICES.get(serv, -1)                
            if serv == -1:
                MsgBox(f"Cannot find social network '{serv}'!", 
                    title='Error', msgtype='error')
                return False
            elif serv == 0:
                just_copy_url = True
        if os.path.isfile(file_or_url):
            # file_or_url is a file, upload it!
            link_info = self.cloud.upload_file(file_or_url)
            if not link_info:
                return False
            file_or_url = link_info.get('url', None)

        if not file_or_url:
            MsgBox(f"Malformed URL or file path!", title='Error', msgtype='error')
            return False

        if just_copy_url:
            # copy link to clipboard and exit
            clipboard_copy(file_or_url)
            MsgBox('Copied link to clipboard!')
            return True

        req = f"{Share.BASEURL}&apikey={Share.APPID}&service={serv}&link={urllib.parse.quote(file_or_url)}"
        if title:
            req += f"&title={urllib.parse.quote(title)}"
        if notes:
            req += f"&notes={urllib.parse.quote(notes)}"
        if url_shortener:
            req += f"&shortener={url_shortener}"
        if tags:
            req += f"&tags={','.join([urllib.parse.quote(t) for t in tags.split(',')])}"
        if source:
            req += f"&source={urllib.parse.quote(source)}"

        if self._request(req, returntype='bool', headers={'Content-Type': 'application/json'}, 
                         error_keymap=Share.ERRMAP, timeout=self.timeout):
            webbrowser.open(req, new=2)
            return True

        return False

