# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.onlineservices
# Provides interfaces for the online services used by the app:
# Yandex and MW online dictionaries, Google search engine, Kloudless cloud storage
# and Shareaholic social sharing service.
import requests, os, uuid, json, webbrowser, time
import urllib.parse
from abc import ABC, abstractmethod

from .globalvars import *
from .utils import MsgBox, UserInput, clipboard_copy, generate_uuid

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Google search interface.
# Executes search with custom parameters using Google's JSON (REST) API
# and returns the results in a Python dictionary.
class GoogleSearch:

    ## @param settings `dict` pointer to the app settings dictionary (`pycross::guisettings::CWSettings::settings`)
    # @param search_phrase `str` search phrase to search in Google
    # @param exact_match `bool` whether to treat the search phrase verbatim (`True`) or
    # fuzzily (`False`)
    # @param file_types `iterable` | `None` if not `None`, Google will present results (documents) only
    # having the indicated file types (extensions), e.g. `['pdf', 'doc', 'docx']`
    # @param lang `iterable` | `None` search documents restricted only to these languages,
    # as listed by GoogleSearch::get_document_languages()
    # @param country `iterable` | `None` only return documents found in these countries,
    # as listed by GoogleSearch::get_document_countries()
    # @param interface_lang `iterable` | `None` search using only selected interface languages,
    # as listed by GoogleSearch::get_interface_languages()
    # @param link_site `str` | `None` link site URL
    # @param related_site `str` | `None` related (parent) site URL
    # @param in_site `str` | `None` URL of a website to search in
    # @param nresults `int` limit number of returned results (-1 = no limit)
    # @param safe_search `bool` turn on Google safe search filter
    # @param timeout `int` network request timeout (in msec.)
    def __init__(self, settings, search_phrase='', exact_match=False, file_types=None, lang=None,
                 country=None, interface_lang=None, link_site=None, related_site=None, in_site=None,
                 nresults=-1, safe_search=False, timeout=5000):
        ## `dict` stored pointer to app global settings
        self.settings = settings
        # init members
        self.init(search_phrase, exact_match, file_types, lang, country, interface_lang, link_site,
                  related_site, in_site, nresults, safe_search, timeout)

    ## Initializes members with params passed to constructor.
    # @param search_phrase `str` search phrase to search in Google
    # @param exact_match `bool` whether to treat the search phrase verbatim (`True`) or
    # fuzzily (`False`)
    # @param file_types `iterable` | `None` if not `None`, Google will present results (documents) only
    # having the indicated file types (extensions), e.g. `['pdf', 'doc', 'docx']`
    # @param lang `iterable` | `None` search documents restricted only to these languages,
    # as listed by GoogleSearch::get_document_languages()
    # @param country `iterable` | `None` only return documents found in these countries,
    # as listed by GoogleSearch::get_document_countries()
    # @param interface_lang `iterable` | `None` search using only selected interface languages,
    # as listed by GoogleSearch::get_interface_languages()
    # @param link_site `str` | `None` link site URL
    # @param related_site `str` | `None` related (parent) site URL
    # @param in_site `str` | `None` URL of a website to search in
    # @param nresults `int` limit number of returned results (-1 = no limit)
    # @param safe_search `bool` turn on Google safe search filter
    # @param timeout `int` network request timeout (in msec.)
    def init(self, search_phrase='', exact_match=False, file_types=None, lang=None,
                 country=None, interface_lang=None, link_site=None, related_site=None, in_site=None,
                 nresults=-1, safe_search=False, timeout=5000):
        ## `str` search phrase to search in Google
        self.search_phrase = search_phrase
        ## `bool` whether to treat the search phrase verbatim
        self.exact_match = exact_match
        ## `iterable` file types (extensions) to include in search results
        self.file_types = file_types
        ## `iterable` search documents restricted only to these languages
        self.lang = lang
        ## `iterable` only return documents found in these countries
        self.country = country
        ## `iterable` search using only selected interface languages
        self.interface_lang = interface_lang
        ## `str` link site URL
        self.link_site = link_site
        ## `str` related (parent) site URL
        self.related_site = related_site
        ## `str` URL of a website to search in
        self.in_site = in_site
        ## `int` limit number of returned results (-1 = no limit)
        self.nresults = nresults if nresults < 10 else 10
        ## `bool` turn on Google safe search filter
        self.safe_search = safe_search
        ## `int` network request timeout (in msec.)
        self.timeout = timeout

    ## Constructs a search query string from the member parameters.
    # @returns `str` parametrized search URL
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

    ## Decodes an URL-encoded string (e.g. converts '%20' to spaces etc.)
    # @param text `str` URL-encoded text
    # @returns `str` decoded text
    def decode_result(self, txt):
        return urllib.parse.unquote(txt)

    ## Returns full Google search results for `GoogleSearch::search_phrase`.
    # @param method `str` parsing method to parse the results
    # @returns `dict` | `str` search results; if `method` == 'json' (default),
    # the results are parsed as a JSON-formatted string into a Python dictionary object.
    # Otherwise, the raw result string is returned.
    def search(self, method='json'):
        req = self.encode_search()
        if DEBUGGING:
            print(_("GOOGLE SEARCH REQUEST = '{}'").format(req))
        proxies = {'http': self.settings['common']['web']['proxy']['http'], 'https': self.settings['common']['web']['proxy']['https']} if not self.settings['common']['web']['proxy']['use_system'] else None
        res = requests.get(req, timeout=self.timeout, proxies=proxies)
        if res:
            if DEBUGGING:
                print(_("GOOGLE SEARCH RESULT = '{}'").format(res.text))
            res = res.json() if method == 'json' else res.content
            if isinstance(res, dict) and 'error' in res:
                raise Exception(_("Request returned error '{}', code = {}").format((res.get('message', 'Invalid request')), (res.get('code', 400))))
            return res
        else:
            raise Exception(_("Request returned error {}").format(res.status_code))

    ## Retrieves search results for `GoogleSearch::search_phrase` as a `list`.
    # @returns `list` search results as a `list` of `dict` objects:
    # ```
    # [{'url': 'URL', 'title': 'TITLE', 'summary': 'SNIPPET'}, ...]
    # ```
    # @see https://developers.google.com/custom-search/v1/cse/list
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

    ## @returns `list` list of Google interface languages
    @staticmethod
    def get_interface_languages():
        return GOOGLE_LANG_HL

    ## @returns `list` list of Google document languages
    @staticmethod
    def get_document_languages():
        return GOOGLE_LANG_LR

    ## @returns `list` list of Google result countries
    @staticmethod
    def get_document_countries():
        return GOOGLE_COUNTRIES_CR

    ## @returns `list` list of Google search countries
    @staticmethod
    def get_user_countries():
        return GOOGLE_COUNTRIES_GL

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## Base (abstract) class for online dictionaries.
class OnlineDictionary(ABC):

    ## @param settings `dict` pointer to the app settings dictionary (`pycross::guisettings::CWSettings::settings`)
    # @param url_template `str` search URL template with placeholders ('{}') for parameters
    # @param timeout `int` network request timeout (in msec.)
    def __init__(self, settings, url_template='', timeout=5000):
        ## str` search URL template with placeholders ('{}') for parameters
        self.url = url_template
        ## `int` network request timeout (in msec.)
        self.timeout = timeout
        ## `dict` stored pointer to app global settings
        self.settings = settings

    ## Constructs the search URL given a search word.
    # @param word `str` search word
    # @returns `str` prepared search URL
    def prepare_request_url(self, word):
        return self.url.format(word)

    ## Returns full definitions for 'word' in JSON (python object) or raw text format.
    # @param word `str` search word
    # @param method `str` parsing method to parse the results
    # @returns `dict` | `str` search results; if `method` == 'json' (default),
    # the results are parsed as a JSON-formatted string into a Python dictionary object.
    # Otherwise, the raw result string is returned.
    def get_definitions(self, word, method='json'):
        req = self.prepare_request_url(word)
        if DEBUGGING:
            print(_("DICTIONARY SEARCH REQUEST = '{}'").format(req))
        proxies = {'http': self.settings['common']['web']['proxy']['http'], 'https': self.settings['common']['web']['proxy']['https']} if not self.settings['common']['web']['proxy']['use_system'] else None
        res = requests.get(self.prepare_request_url(word), timeout=self.timeout, proxies=proxies)
        if res:
            if DEBUGGING:
                print(_("DICTIONARY SEARCH RESULT = '{}'").format(res.text))
            return res.json() if method == 'json' else res.content
        else:
            raise Exception(_("Request returned error {}").format(res.status_code))

    ## Returns the abridged definition for the given entry.
    # @param word `str` the word query
    # @param exact_match `bool` if `True`, only defitions for the exact word given by `word` will be returned
    # @param partsofspeech `list`|`tuple` parts of speech to get definitions for
    # (`None` = all available)
    # @param bad_pos `str` substitution for part of speech if unavailable
    # @returns `list` list of short definitions in the format:
    # ```
    # [('word', 'part of speech', [list of defs], 'url'), ...]
    # ```
    @abstractmethod
    def get_short_defs(self, word, exact_match=True, partsofspeech=None, bad_pos='UNKNOWN'):
        return []

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## Interface for [Merriam-Webster Collegiate dictionary](https://www.dictionaryapi.com).
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

## Interface for [Yandex dictionary](https://tech.yandex.com/dictionary/).
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

## @brief Interface for the [Kloudless cloud storage API](https://kloudless.com/cloud-storage-api/).
# Kloudless lets user apps integrate a number of external storage services (like DropBox or Google Drive)
# and access data via a single API. **pycrossword** uses a registered app on Kloudless (`pycross`)
# that is tied to a default DropBox file storage account.
# Most methods deal with fildes and folders referencing them by their unique IDs
# (hash strings).
# Read the [Kloudless docs](https://kloudless.com/unified-api/) to learn more.
class Cloudstorage:

    ## base URL for Kloudless Storage API (version 2)
    APIURL = 'https://api.kloudless.com/v2/'
    ## DropBox account ID (connected to the pycross app on Kloudless)
    ACCID = 352604900
    ## root folder name on DropBox
    ROOTNAME = 'pycrossall'
    #ROOTID = 'Fn6Cw1UD_PxkjIc8EN8u0uF4LYc2hdbgF8VEy6eS7eyg='
    ## pycrossword app ID on Kloudless
    APP_ID = 'RXaPpmxluGS7vMYoWfve847PzGuvPVdbunZe2W_vJKQdvxzx'
    ## base URL for OAuth 2.0 authorization chain
    OAUTH_URL = f"https://api.kloudless.com/v1/oauth/?client_id={APP_ID}&response_type=token&redirect_uri=urn:ietf:wg:oauth:2.0:oob&scope=dropbox&state={{}}"

    ## @param settings `dict` pointer to the app settings dictionary (`pycross::guisettings::CWSettings::settings`)
    # @param auto_create_user `bool` create a new user account if the user ID stored
    # in the app global settings is not active / not found
    # @param on_user_exist `callable` callback function called when the user with
    # the name stored in the app settings already exists. The callback tales one
    # parameter -- the user name, and returns a Boolean value: `True` to go on
    # with that user name, `False` to cancel
    # @param on_update_users `callable` callback function fired when the user list
    # (list of users connected to the cloud) is updated; it takes one argument --
    # a `list` of users and returns nothing
    # @param on_error `callable` callback function fired when an exception is raised;
    # it takes a single argument -- the error message
    # @param show_errors `bool` whether to display error messages in GUI dialogs
    # @param on_apikey_required `callable` callback function called when the app
    # requires the user to enter a Kloudless API key; it takes one argument --
    # a list containing two elements:
    #   * `str` the API key entered by the user
    #   * `bool` user action result: `True` = use the API key, `False` = cancel
    # @param on_bearer_required `callable` callback function called when the app
    # requires the user to enter a Kloudless Bearer Token; it takes one argument --
    # a list containing two elements:
    #   * `str` the Bearer Token entered by the user
    #   * `bool` user action result: `True` = use the Bearer Token, `False` = cancel
    # @param timeout `int` network request timeout (in msec.)
    def __init__(self, settings, auto_create_user=False,
                 on_user_exist=None, on_update_users=None, on_error=None,
                 show_errors=False, on_apikey_required=None, on_bearer_required=None,
                 timeout=5000):
        ## `dict` stored pointer to app global settings
        self.settings = settings
        ## `int` network request timeout (in msec.)
        self.timeout = timeout
        ## `callable` callback function called when the user with
        # the name stored in the app settings already exists
        self.on_user_exist = on_user_exist
        ## `callable` callback function fired when the user list
        # (list of users connected to the cloud) is updated
        self.on_update_users = on_update_users
        ## `callable` callback function fired when an exception is raised
        self.on_error = on_error
        ## `bool` whether to display error messages in GUI dialogs
        self.show_errors = show_errors
        ## `callable` callback function called when the app
        # requires the user to enter a Kloudless API key
        self.on_apikey_required = on_apikey_required
        ## `callable` callback function called when the app
        # requires the user to enter a Kloudless Bearer Token
        self.on_bearer_required = on_bearer_required
        ## `list` list of users connected to the cloud
        self.users = []
        # initialize settings
        self.init_settings(auto_create_user)

    ## Initializes the Kloudless config, optionally creating the user account and folders.
    # @param auto_create_user `bool` create a new user account if the user ID stored
    # in the app global settings is not active / not found
    def init_settings(self, auto_create_user=True):
        # get valid Bearer Token or API key before anything else
        if not self._authenticate():
            self._error(_('Failed to authenticate!'), raise_error=True)
        if not getattr(self, '_accid', None):
            ## `str` Kloudless account ID
            self._accid = self.settings['sharing']['account'] or Cloudstorage.ACCID
        ## `str` base URL for REST requests to the Kloudless API
        self._baseurl = f"{Cloudstorage.APIURL}accounts/{self._accid}/storage/"
        ## `str` root folder ID in the DropBox storage
        self._rootid = ''
        rootname = self.settings['sharing']['root_folder'] \
            if (self.settings['sharing']['root_folder'] and self.settings['sharing']['account'] \
                and self.settings['sharing']['bearer_token']) else Cloudstorage.ROOTNAME
        new_folder = self._create_folder(rootname)
        if new_folder:
            self._rootid = new_folder[1]
            self.settings['root_folder'] = '' if new_folder[0] == Cloudstorage.ROOTNAME else new_folder[0]
        else:
            self._error(_("Unable to create/access folder '{}'!").format(rootname))

        if auto_create_user:
            self._find_or_create_user(self.settings['sharing']['user'], True)
        else:
            self._update_users()

    ## Authenticates the user using either the API key or the Bearer Token.
    # @param force_api_key `bool` if `True`, the API key will be demanded regardless
    # of the existing Bearer Token (used for admin operations)
    # @returns `str` | `None` the authentication method used ('APIKey' or 'Bearer')
    # or `None` on failure to authenticate
    def _authenticate(self, force_api_key=False):
        if self.settings['sharing']['use_api_key'] or force_api_key:
            self._get_apikey()
            if not self._apikey:
                self._error(_('No valid API key provided!\nProvide a valid API key or change your "use_api_key" settings\nto use a different authentication method.'), raise_error=True)
                return None
            return 'APIKey'
        else:
            self._get_bearer()
            if not self._bearer:
                self._error(_('No valid Bearer token provided!\nProvide a valid Bearer token or change your "use_api_key" settings\nto use a different authentication method.'), raise_error=True)
                return None
            if not self._check_bearer():
                self._error(_('Bearer token is invalid or expired!'))
                return None
            return 'Bearer'

    ## Shows an error message or raises an exception. Calls `Cloudstorage::on_error`.
    # @param message `str` the error / exception message
    # @param code `str` code fragment where the exceptio has occurred
    # @param title `str` error dialog title (caption)
    # @param msgtype `str` error dialog type (icon) as given in utils::MsgBox()
    # @param raise_error `bool` if `True`, an Exception will be raised reporting
    # that error
    # @exception `Exception` if `raise_error` is `True`
    def _error(self, message, code=None, title=_('Error'), msgtype='error', raise_error=False):
        if self.show_errors:
            MsgBox(message, title=title, msgtype=msgtype)
        if self.on_error:
            self.on_error(self._error_tostr({'message': message, 'code': code}))
        if raise_error:
            raise Exception(message)

    ## Converts an error dictionary object into a single string.
    # @param error `dict` | `str` error data with 2 keys: 'message' (error message)
    # and 'code' (the code fragment that caused the error); or a prepared error message
    # @returns `str` formatted error message
    def _error_tostr(self, error):
        if isinstance(error, str):
            return error
        if isinstance(error, dict):
            return f"{error['message']}{('{NEWLINE}[' + error['code'] + ']') if error['code'] else ''}"
        return str(error)

    ## Sumbits an HTTP(S) request to a URL and returns the result.
    # @param url `str` the requested URL
    # @param command `str` any of the four HTTP(S) verbs:
    #   * 'get' the GET command
    #   * 'post' the POST command
    #   * 'delete' the DELETE command
    #   * 'update' the UPDATE command
    # @param returntype `str` type of the returned results; any of:
    #   * 'json' (default) Python dictionary constructed from JSON text
    #   * 'bool' Boolean value (`True` or `False`)
    #   * 'text' Unicode-formatted text
    #   * <anything else> raw result contents (bytes)
    # @param error_keymap `dict` dictionary mapping the error message and code
    # to the keys in the JSON result
    # @param kwargs `keyword arguments` additional args that may be passed
    # to the `requests` methods (like `timeout`, `proxies` etc.)
    # @returns `dict`|`str`|`bool`|`bytes` request result depending on the value
    # of `returntype`
    def _request(self, url, command='get', returntype='json',
                 error_keymap={'message': 'message', 'code': 'status_code'},
                 **kwargs):

        if DEBUGGING:
            print(_("CLOUD SENDING '{}' REQUEST = '{}',\n"
                  "HEADERS = {},\n"
                  "DATA = {}").format(command, url, kwargs.get('headers', None), kwargs.get('data', None)))

        methods = {'get': requests.get, 'post': requests.post, 'delete': requests.delete,
                   'patch': requests.patch}
        res = None
        try:
            kwargs['timeout'] = kwargs.get('timeout', self.timeout)
            if not self.settings['common']['web']['proxy']['use_system']:
                kwargs['proxies'] = {'http': self.settings['common']['web']['proxy']['http'], 'https': self.settings['common']['web']['proxy']['https']}
            res = methods[command](url, **kwargs)
            if res is None: raise Exception(_("Empty result returned by request '{}'").format(url))
            if DEBUGGING:
                print(_("CLOUD REQUEST RESULT = '{}'").format(res.text))
            if not res:
                try:
                    err = res.json()
                except:
                    err = {}
                self._error(str(err.get(error_keymap['message'], _("Error returned by request '{}'").format(url))),
                            err.get(error_keymap['code'], None))
                return None if returntype != 'bool' else False

        except Exception as e:
            self._error(str(e))
            return None if returntype != 'bool' else False

        if returntype == 'bool': return True
        if returntype == 'json': return res.json()
        if returntype == 'text': return res.text
        return res.content

    ## Unless no Kloudless API key is stored in Cloudstorage::_apikey, asks the user
    # to provide one.
    def _get_apikey(self):
        if not getattr(self, '_apikey', None):
            res = [None, False]
            if self.on_apikey_required:
                self.on_apikey_required(res)
                while res[0] is None: time.sleep(100)
            else:
                res = UserInput(label=_('Enter your API key'), textmode='password')
            ## `str` the stored API key
            self._apikey = res[0] if res[1] else None

    ## Unless no Bearer Token is stored in Cloudstorage::_bearer, asks the user
    # to provide one.
    def _get_bearer(self):
        self._bearer = self.settings['sharing'].get('bearer_token', None)
        if self._bearer:
            return
        res = [None, False]
        if self.on_bearer_required:
            self.on_bearer_required(res)
            while res[0] is None: time.sleep(100)
        else:
            # TODO: authorize via browser
            res = UserInput(label=_('Enter your Bearer token'), textmode='password')
        ## `str` the stored Bearer Token
        self._bearer = res[0] if res[1] else None

    ## Validates the provided Bearer Token againt the app ID in Kloudless.
    # @param bearer_token `str` the user's Bearer Token; if `None`, it will
    # be retrieved from Cloudstorage::_bearer
    # @returns `bool` `True` if the Bearer Token has been successfully validated;
    # `False` otherwise
    def _check_bearer(self, bearer_token=None):
        self._accid = None
        if not bearer_token:
            bearer_token = getattr(self, '_bearer', None)
        if not bearer_token:
            return False
        res = self._request('https://api.kloudless.com/v1/oauth/token',
                            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {bearer_token}"})
        if res and res.get('client_id', '') == Cloudstorage.APP_ID:
            self._accid = res.get('account_id', None)
            if self._accid:
                self.settings['sharing']['account'] = str(self._accid)
                self.settings['sharing']['bearer_token'] = bearer_token
                return True
            return False
        return False

    ## Authenticates the user for an operation and returns the corresponding headers.
    # @param content_type `str` application content type string
    # @param force_api_key `bool` demand API key unconditionally
    # @returns `dict`|`None` HTTP(S) headers with content type and auth details
    # or `None` if failed to authorize user
    def _make_headers(self, content_type='application/json', force_api_key=False):
        auth = self._authenticate(force_api_key)
        if auth == 'APIKey':
            return {'Content-Type': content_type, 'Authorization': f"APIKey {self._apikey}"}
        elif auth == 'Bearer':
            return {'Content-Type': content_type, 'Authorization': f"Bearer {self._bearer}"}
        else:
            return None

    ##  Service method: lists all accounts tied to the pycross app on Kloudless.
    # @param enabled `bool`|`None` list only enabled or disabled accounts;
    # `None` = list all
    # @param admin `bool`|`None` list only admin/non-admin accounts; `None` = list all
    # @param search `str` search string to locate specific users
    # @returns `dict` accounts data
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/authentication#accounts-list-accounts-get)
    def _get_accounts(self, enabled=None, admin=None, search=None):
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

    ## Service method: gets metadata for account specified by 'account_id'.
    # @param account_id `str` requested account ID
    # @param retrieve_tokens `bool` include Bearer Tokens in result
    # @param retrieve_full `bool` include full account info in result (like quota etc.)
    # @returns `dict` account metadata
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/authentication#accounts-retrieve-an-account-get)
    def _get_account_matadata(self, account_id, retrieve_tokens=False, retrieve_full=True):
        req = f"{Cloudstorage.APIURL}accounts/{account_id}/?retrieve_tokens={str(retrieve_tokens).lower()}&retrieve_full={str(retrieve_full).lower()}"
        return self._request(req, headers=self._make_headers(force_api_key=True))

    ## Retrieves storage quota information.
    # @returns `dict` storage quota info
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#other-storage-quota-get)
    def _get_quota(self):
        req = f"{self._baseurl}quota"
        return self._request(req, headers=self._make_headers())

    ## Lists items in a folder.
    # @param fid `str` folder ID
    # @param recurse `bool` recurse into subfolders
    # @returns `dict` folder elements (subfolders and files)
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#folders-retrieve-folder-contents-get)
    def _get_folder_objects(self, fid, recurse=False):
        if not fid:
            self._error(_('Empty folder ID passed to _get_folder_objects()!'))
            return None
        req = f"{self._baseurl}folders/{urllib.parse.quote(fid)}/contents/?recursive={str(recurse).lower()}"
        return self._request(req, headers=self._make_headers())

    ## Gets a folder's parent folders (ancestors).
    # @param folder_id `str` folder ID
    # @returns `dict` folder ancestors
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#folders-retrieve-folder-metadata-get)
    def _get_folder_ancestors(self, folder_id):
        folder_info = self._get_folder_metadata(folder_id)
        if not folder_info: return None
        return folder_info.get('ancestors', None)

    ## Checks if given folder is inside current user's folder.
    # @param folder_id `str` folder ID
    # @returns `bool` `True` if the given folder is inside the current user's
    # root folder; `False` otherwise
    def _is_user_folder(self, folder_id):
        if not self._user: return False
        ancestors = self._get_folder_ancestors(folder_id)
        if not ancestors: return False
        for anc in ancestors:
            index = 2 if anc['id_type'] == 'path' else 1
            if anc['id'] == self._user[index]:
                return True
        return False

    ## Generates a randon user name (GUID).
    # @returns `str` new user name
    def _generate_username(self):
        while True:
            usr = uuid.uuid4().hex
            for u in self.users:
                if u[0] == usr:
                    break
            else:
                return usr

    ## Creates a new folder within the current user's space on DropBox.
    # @param folder_name `str` the new folder name
    # @param parent_id `str` the ID of the parent folder (where the new one is to be created)
    # @param error_on_exist `bool` cancel operation if the folder with that name
    # already exists in the indicated location; if `False`, the existing folder
    # will be used
    # @returns `tuple`|`None` tuple containing the new folder data:
    #   1. folder name
    #   2. folder ID
    #   3. full path to folder
    # In case of failure (e.g. when the folder exists and `error_on_exist` is `True`),
    # returns `None`.
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#folders-create-a-folder-post)
    def _create_folder(self, folder_name, parent_id='root', error_on_exist=False):
        folder_name = folder_name.lower()
        data = {'parent_id': parent_id, 'name': folder_name}
        req = f"{self._baseurl}folders/?conflict_if_exists={str(error_on_exist).lower()}"
        res = self._request(req, 'post', headers=self._make_headers(), json=data)
        return (res['name'], res['id'], res['ids']['path']) if res else None

    ## @brief Updates the list of subfolders present in `dropbox/pycrossall` root folder.
    # The names of these subfolders correspond to the names of the
    # registered users. Each element in `Cloudstorage::users` is a 3-tuple:
    #   1. user name (in lower case)
    #   2. user ID (unique hash string)
    #   3. path to user's root folder
    def _update_users(self):
        res = self._get_folder_objects(self._rootid)
        self.users = []
        if res:
            for obj in res['objects']:
                if obj['type'] != 'folder': continue
                self.users.append((obj['name'].lower(), obj['id'], obj['ids']['path']))
        if self.on_update_users:
            self.on_update_users(self.users)

    ## Retrieves the metadata of the given file: name, path, size, date, etc.
    # @param file_id `str` the ID of the requested file
    # @see _get_folder_metadata()
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#files-retrieve-file-metadata-get)
    def _get_file_metadata(self, file_id):
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/"
        return self._request(req, headers=self._make_headers())

    ## @brief Retrieves the metadata of the given folder: name, path, size, date, etc.
    # If `folder_id` is `None`, the current user's folder will be used.
    # @param folder_id `str` the ID of the requested folder
    # @see _get_file_metadata()
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#folders-retrieve-folder-metadata-get)
    def _get_folder_metadata(self, folder_id=None):
        if not folder_id:
            if not self._user:
                self._error(_('Neither the folder ID not the user ID is valid!'))
                return None
            folder_id = self._user[1]
        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/"
        return self._request(req, headers=self._make_headers())

    ## @brief Checks if a user with the given name exists.
    # Internally, it checks if a folder with that user name exists in the
    # root folder. Remember that folders placed in the root folder (1-level folders)
    # correspond to user 'accounts'. Each user can operate only within his/her folder.
    # @param username `str` name of the user to check
    # @param update_user_list `bool` whether the user list (`Cloudstorage::users`)
    # must first be refreshed from the server
    # @returns `tuple`|`None` 3-tuple containing information on the existing
    # user if the user is found (see _update_users()), or `None` if the user
    # is not found
    def _user_exists(self, username, update_user_list=False):
        if update_user_list: self._update_users()
        username = username.lower()
        for u in self.users:
            if u[0] == username: return u
        return None

    ## @brief Creates or finds a user folder in `dropbox/pycrossall/<username>`.
    # @param username `str` user name to find or create. If `None` (default),
    # a new unique name will be generated with _generate_username().
    # Otherwise, the behavior depends on the result of `Cloudstorage::on_user_exist`
    # callback: if it is set and returns `True`, the found user will be
    # stored as the current user (`Cloudstorage::_user`) and saved to the
    # app global settings. Otherwise, the methods returns `False`.
    # @param update_user_list `bool` whether the user list (`Cloudstorage::users`)
    # must first be refreshed from the server
    def _find_or_create_user(self, username=None, update_user_list=False):

        ## @brief `tuple` current user; contains 3 elements:
        #   1. user name (in lower case)
        #   2. user ID (unique hash string)
        #   3. path to user's root folder
        self._user = None

        if username:

            u = self._user_exists(username, update_user_list)
            if u:
                if not self.on_user_exist or self.on_user_exist(username):
                    # if on_user_exist is not set, or if it returns True,
                    # assign the existing user data to the current one
                    self._user = u
                    self.settings['sharing']['user'] = u[0]
                    return True
                else:
                    # otherwise, return False
                    return False

        else:
            username = self._generate_username()

        new_user = self._create_folder(username, self._rootid)
        if new_user:
            self.users.append(new_user)
            self._user = new_user
            self.settings['sharing']['user'] = username
            return True
        return False

    ## @brief Deletes a user permanently.
    # This in effect deletes the corresponding user's root folder from the
    # app root folder on DropBox (`pycrossall/<username>`), naturally
    # erasing all its contents.
    # @param username `str`|`None` name of the user to delete; if `None`, the current
    # user will be deleted
    # @warning Note that you cannot delete other users unless authorized by
    # the application API Key on Kloudless!
    # @returns `bool` `True` on success, `False` on failure
    def _delete_user(self, username=None):
        if username and self._user and username != self._user[0]:
            self._get_apikey()
            if not self._apikey:
                self._error(_('You can delete other users only with a valid API key!'))
                return False
            user_folder = self._create_folder(username, self._rootid)
            return self.delete_folder(user_folder[1]) if user_folder else False
        elif self._user:
            return self.delete_folder(self._user[1])
        MsgBox(_('No current user present!'), title=_('Error'), msgtype='error')
        return False

    ## Finds or creates a new subfolder in the current user's folder.
    # @param folder_name `str` new folder name
    # @returns `tuple`|`None` the result of _create_folder()
    def find_or_create_folder(self, folder_name):
        return self._create_folder(folder_name, self._user[1], False)

    ## Clears given (sub)folder.
    # @param folder_id `str`|`None` ID of the folder to clear;
    # if `None` (default), the current user's root folder will be used
    # @returns `bool` `True` on success, `False` on failure
    def clear_folder(self, folder_id=None):
        if not folder_id:
            if not self._user:
                self._error(_('Neither the folder ID not the user ID is valid!'))
                return False
            folder_id = self._user[1]
        elif not self._is_user_folder(folder_id):
            # check if folder is in current user's folder
            self._get_apikey()
            if not self._apikey:
                self._error(_('You cannot clear folders created by other users without a valid API key!'))
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
                    res = self._request(req, 'delete', 'bool', headers=self._make_headers('application/octet-stream'))
                    results.append(res)
                except Exception:
                    results.append(False)

        return all(results)

    ## Deletes the folder with the given ID, optionally permanently.
    # @param folder_id `str` ID of the folder to clear
    # @param permanent `bool` whether to delete the folder permanently
    # @param recurse `bool` whether to recurse into subdirectories
    # (effectively clearing **everything** in that folder)
    # @returns `bool` `True` on success, `False` on failure
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#folders-delete-a-folder-delete)
    def delete_folder(self, folder_id, permanent=True, recurse=True):
        if not folder_id:
            self._error(_('No folder ID provided'))
            return False

        # check if folder is in current user's folder
        if not self._is_user_folder(folder_id):
            self._get_apikey()
            if not self._apikey:
                self._error(_('You cannot clear folders created by other users without a valid API key!'))
                return False

        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/?permanent={str(permanent).lower()}&recursive={str(recurse).lower()}"
        return self._request(req, 'delete', 'bool', headers=self._make_headers('application/octet-stream'))

    ## Renames the given (sub)folder.
    # @param folder_id `str` ID of the folder to clear
    # @param new_name `str` new folder name
    # @returns `tuple`|`None` the tuple ('folder name', 'folder id') on success
    # or `None` on failure
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#folders-rename-move-a-folder-patch)
    def rename_folder(self, folder_id, new_name):
        req = f"{self._baseurl}folders/{urllib.parse.quote(folder_id)}/"
        data = {'name': new_name}
        res = self._request(req, 'patch', headers=self._make_headers(), json=data)
        return (res['name'], res['id'], res['ids']['path']) if res else None

    ## Uploads a file into the current user's folder (optionally subfolder) and returns the link info.
    # @param filepath `str` full path to the local file to upload
    # @param folder_id `str`|`None` ID of the folder to clear;
    # if `None` (default), the current user's root folder will be used
    # @param overwrite `bool` whether to overwrite the existing file, if found;
    # if `True`, the first file with the same name will be overwritten;
    # if `False`, the uploaded file will be automatically renamed
    # @param makelink `bool` whether to generate a permanent external link (URL)
    # to the uploaded file (e.g. to share it)
    # @param activelink `bool` `True` to enable the external link, `False`
    # to disable it
    # @param directlink `bool` `True` to make the external link direct, `False`
    # to use redirection
    # @param expire `datetime`|`None` expiry date&time for the link
    # (`None` = never expire)
    # @param password `str`|`None` password to protect the link for downloading
    # (`None` = don't protect)
    # @returns `dict`|`None` the result of create_file_link() or `None` on failure
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#files-upload-a-file-post)
    def upload_file(self, filepath, folder_id=None, overwrite=False,
                    makelink=True, activelink=True,
                    directlink=True, expire=None, password=None):
        if getattr(self, '_user', None) is None:
            self._error(_('Current user is not defined! Please create new user first.'))
            return None
        if not os.path.isfile(filepath):
            self._error(_("File '{}' is not accessable!").format(filepath))
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

    ## Deletes the file with the given ID, optionally permanently.
    # @param file_id `str` ID of the file to delete
    # @param permanent `bool` whether to delete the file permanently
    # @returns `bool` `True` on success, `False` on failure
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#files-delete-a-file-delete)
    def delete_file(self, file_id, permanent=True):
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/?permanent={str(permanent).lower()}"
        return self._request(req, 'delete', 'bool', headers=self._make_headers('application/octet-stream'))

    ## Renames the given file (in the original folder).
    # @param file_id `str` ID of the file to rename
    # @param new_name `str` new file name
    # @returns `tuple`|`None` the tuple ('file name', 'file id') on success
    # or `None` on failure
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#files-rename-move-a-file-patch)
    def rename_file(self, file_id, new_name):
        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/"
        data = {'name': new_name}
        res = self._request(req, 'patch', headers=self._make_headers(), json=data)
        return (res['name'], res['id'], res['ids']['path']) if res else None

    ## Downloads the given file and saves it to a local folder.
    # @param file_id `str` ID of the file to download
    # @param save_folder `str` path to a local folder to save the file;
    # if empty (default), the current working directory is used
    # @param overwrite `bool` whether to overwrite existing files
    # (if `False`, an error is displayed)
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#files-download-a-file-get)
    def download_file(self, file_id, save_folder='', overwrite=False):
        file_info = self._get_file_metadata(file_id)
        if not save_folder:
            save_folder = os.getcwd()
        filepath = os.path.join(os.path.abspath(save_folder), file_info['name'] if file_info else 'UNKNOWN_FILE')
        if not overwrite and os.path.isfile(filepath):
            self._error(_("File '{}' already exists!").format(filepath), msgtype='warn')
            return False

        req = f"{self._baseurl}files/{urllib.parse.quote(file_id)}/contents/"
        res = self._request(req, returntype='content',
                            headers=self._make_headers(file_info['mime_type'] if file_info \
                            else 'application/octet-stream'), allow_redirects=True)
        if not res: return False
        with open(filepath, 'wb') as fout:
            fout.write(res)
        return True

    ## Creates a public link to the specified file (given by a file ID).
    # @param file_id `str` ID of the file
    # @param activelink `bool` `True` to enable the external link, `False`
    # to disable it
    # @param directlink `bool` `True` to make the external link direct, `False`
    # to use redirection
    # @param expire `datetime`|`None` expiry date&time for the link
    # (`None` = never expire)
    # @param password `str`|`None` password to protect the link for downloading
    # (`None` = don't protect)
    # @returns `dict`|`None` the link meta info or `None` on failure
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#links-create-a-link-post)
    def create_file_link(self, file_id, activelink=True, directlink=True,
                         expire=None, password=None):
        if not file_id:
            self._error(_('Empty file ID passed to create_file_link()!'))
            return None

        req = f"{self._baseurl}links/"
        data = {'file_id': file_id, 'direct': directlink, 'active': activelink}
        if not expire is None:
            data['expiration'] = expire.isoformat()
        if not password is None:
            data['password'] = password
        return self._request(req, 'post', headers=self._make_headers(), json=data)

    ## Retrieves file link info (given by link ID).
    # @param link_id `str` ID of the file link
    # @returns `dict` the link meta info
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#links-retrieve-a-link-get)
    def get_file_link(self, link_id):
        if not link_id:
            self._error(_('Empty link ID passed to get_file_link()!'))
            return None
        req = f"{self._baseurl}links/{urllib.parse.quote(link_id)}/"
        return self._request(req, headers=self._make_headers())

    ## Updates the public link to the specified file (given by file ID).
    # @param link_id `str` ID of the file link
    # @param activelink `bool` `True` to enable the external link, `False`
    # to disable it
    # @param expire `datetime`|`None` expiry date&time for the link
    # (`None` = never expire)
    # @param password `str`|`None` password to protect the link for downloading
    # (`None` = don't protect)
    # @returns `dict`|`None` the link meta info or `None` on failure
    # @see [Kloudless docs](https://developers.kloudless.com/docs/v1/storage#links-update-a-link-patch)
    def update_file_link(self, link_id, activelink=None,
                         expire=None, password=None):
        if not link_id:
            self._error(_('Empty link ID passed to update_file_link()!'))
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

    ## Deletes the public link to the specified file (given by file ID).
    # @param link_id `str` ID of the file link
    # @returns `bool` `True` on success / `False` on failure
    def delete_file_link(self, link_id):
        if not link_id:
            self._error(_('Empty link ID passed to delete_file_link()!'))
            return None

        req = f"{self._baseurl}links/{urllib.parse.quote(link_id)}/"
        return self._request(req, 'delete', 'bool', headers=self._make_headers())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Interface class for the [Shareaholic service](https://www.shareaholic.com/).
# The application has a free account on Shareaholic to enable social sharing,
# i.e. posting text / URLs to your Twitter, Facebook and other social networks.
# @see [Shareaholic Share API docs](https://www.shareaholic.com/api/)
class Share:

    ## ID of pycrossword app on Shareaholic
    APPID = 'abf1b67f10817416ba9fee9b76455bef'
    ## base URL for Shareaholic API requests
    BASEURL = 'https://www.shareaholic.com/api/share/?v=1&apitype=1'
    ## error message key map
    ERRMAP = {'message': 'data', 'code': 'code'}
    ## enabled social networks and their Shareaholic internal numbers
    SERVICES = {'twitter': 7, 'facebook': 5, 'pinterest': 309, 'linkedin': 88, 'gmail': 52,
                'yahoomail': 54, 'aolmail': 55, 'hotmail': 53, 'myspace': 39,
                'reddit': 40, 'skype': 989, 'tumblr': 78, 'yandex': 267, 'clipboard': 0}

    ## @param cloud `Cloudstorage` pointer to a `Cloudstorage` object
    # @param on_upload `callable` function called when a file is uploaded
    # to the cloud storage; takes to args:
    #   1. `str` full path to the uploaded file
    #   2. `str` generated public link (URL)
    # @param on_clipboard_write `callable` callback called when data is written
    # to the system clipboard (as one sharing option); takes one arg:
    # `str` generated public link (URL)
    # @param on_prepare_url `callable` callback called when the request URL
    # to Shareaholic is prepared; takes one arg: `str` the request URL
    # @param stop_check `callable` callback that takes no arguments
    # and returns `True` to stop the current sharing operation or
    # `False` to continue
    # @param timeout `int` network request timeout (in msec)
    def __init__(self, cloud: Cloudstorage, on_upload=None, on_clipboard_write=None,
                 on_prepare_url=None, stop_check=None, timeout=5000):
        ## `callable` function called when a file is uploaded
        self.on_upload = on_upload
        ## `callable` callback called when data is written
        # to the system clipboard (as one sharing option)
        self.on_clipboard_write = on_clipboard_write
        ## `callable` callback called when the request URL
        # to Shareaholic is prepared
        self.on_prepare_url = on_prepare_url
        ## `callable` callback that takes no arguments
        # and returns `True` to stop the current sharing operation or
        # `False` to continue
        self.stop_check = stop_check
        ## `int` network request timeout (in msec)
        self.timeout = timeout
        if not cloud:
            raise Exception(_('Share object must be given a valid instance of Cloudstorage as the "cloud" argument!'))
        ## `Cloudstorage` pointer to the `Cloudstorage` object
        self.cloud = cloud

    ## @brief Shares a given URL or file in selected social networks.
    # This method is the main interface for the application, since it
    # encapsulates the lower-level cloud storage functionality to
    # upload files and create public links.
    # @warning This method is called in a separate thread, so it is designed
    # for maximum thread safety. That is also the reason why it doesn't
    # return any results but rather replies on callback functions.
    # @param file_or_url `str` full path to a local file or a prepared link (URL)
    # @param social `str` social network short name, e.g. 'twitter' --
    # see Share::SERVICES
    # @param title `str` title (caption) for your post
    # @param notes `str` message body for your post
    # @param url_shortener `str` URL shortening service to shorten
    # your link URL; see [Shareaholic docs](https://www.shareaholic.com/api/)
    # for available options
    # @param tags `str` comma-separated tags for your post
    # @param source `str` name of the sharing app ('pycrossword')
    def share(self, file_or_url, social='twitter',
              title='My new crossword', notes=_('See my new crossword'),
              url_shortener='shrlc', tags='pycrossword,crossword,python',
              source='pycrossword'):

        serv = social
        just_copy_url = False

        if isinstance(serv, str):
            serv = Share.SERVICES.get(serv, -1)
            if serv == -1:
                self.cloud._error(_("Cannot find social network '{}'!").format(serv))
                return
            elif serv == 0:
                just_copy_url = True

        if os.path.isfile(file_or_url):
            # file_or_url is a file, upload it!
            link_info = self.cloud.upload_file(file_or_url)
            if not link_info:
                return
            if self.stop_check and self.stop_check(): return
            url = link_info.get('url', None)
            if self.on_upload:
                self.on_upload(file_or_url, url)
            file_or_url = url

        if not file_or_url:
            self.cloud._error(_('Malformed URL or file path!'))
            return

        if just_copy_url:
            # copy link to clipboard and exit
            if self.on_clipboard_write:
                self.on_clipboard_write(file_or_url)
            else:
                clipboard_copy(file_or_url)
            return

        if self.stop_check and self.stop_check(): return

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

        if self.on_prepare_url:
            self.on_prepare_url(req)

        elif self.cloud._request(req, returntype='bool', headers={'Content-Type': 'application/json'},
                                   error_keymap=Share.ERRMAP, timeout=self.timeout):
            webbrowser.open(req, new=2)

