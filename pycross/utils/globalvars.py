# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.globalvars
import os, gettext

def make_abspath(filename, root=''):
    # default root = pycross
    if not root: root = os.path.dirname(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(root, filename))

## toggle debug messages
DEBUGGING = False

## current app version
APP_VERSION = '0.3'

## app name
APP_NAME = 'pycrossword'

# git repo
GIT_REPO = 'https://github.com/S0mbre/crossword.git'

# app author
APP_AUTHOR = 'Iskander Shafikov (S0mbre)'

# author's email
APP_EMAIL = 's00mbre@gmail.com'

# default encoding
ENCODING = 'utf-8'

SETTINGS_FILE = make_abspath('settings.pxjson')
DEFAULT_SETTINGS_FILE = make_abspath('defsettings.pxjson')
UPDATE_FILE = make_abspath('update.json')
SAVEDCW_FILE = make_abspath('autosaved.xpf')
DICFOLDER = make_abspath('assets/dic')
ICONFOLDER = make_abspath('assets/icons')
PLUGINS_FOLDER = make_abspath('plugins')
LANG = {'en': 'English', 'ru': 'Russian', 'fr': 'French', 'es': 'Spanish', 'de': 'German', 'it': 'Italian'}
POS = [('N', 'noun'), ('V', 'verb'), ('ADV', 'adverb'), ('ADJ', 'adjective'), ('P', 'participle'), 
       ('PRON', 'pronoun'), ('I', 'interjection'), ('C', 'conjuction'), ('PREP', 'preposition'), 
       ('PROP', 'proposition'), ('MISC', 'miscellaneous / other'), ('NONE', 'no POS')]        
BRACES = "{}"
SQL_TABLES = {'words': {'table': 'twords', 'fwords': 'word', 'fpos': 'idpos'},
              'pos':   {'table': 'tpos', 'fid': 'id', 'fpos': 'pos'} }
        
HTTP_PROXIES = None # or dict, e.g. {'http': 'http://ip:port', 'https': 'http://ip:port'}
HTTP_TIMEOUT = 5                 # ожидание соединения и ответа (сек.) None = вечно
MAX_RESULTS = 500
PLUGIN_EXTENSION = 'pxplugin'
PLUGIN_TEMPLATE_GENERAL = """\
from utils.pluginbase import *

class PxPlugin000(PxPluginGeneral):

    # >>> add code here <<<
    pass
"""

APP_LANGUAGES = [('English (US)', '', '', 'united-states-of-america.png', "The application must be restarted to apply new language settings. Restart now?"), 
                 ('Russian', 'ru', 'Русский', 'russia.png', "Приложение должно быть перезапущено для применения новых настроек языка. Перезапустить сейчас?"), 
                 ('German', 'de', 'Deutsch', 'germany.png', "Die Anwendung muss neu gestartet werden, um neue Spracheinstellungen zu übernehmen. Jetzt neu starten?"), 
                 ('French', 'fr', 'Français', 'france.png', "L'application doit être redémarrée pour appliquer de nouveaux paramètres de langue. Redémarrer maintenant?"), 
                 ('Italian', 'it', 'Italiano', 'italy.png', "È necessario riavviare l'applicazione per applicare le nuove impostazioni della lingua. Riavvia ora?"), 
                 ('Spanish', 'es', 'Español', 'spain.png', "La aplicación debe reiniciarse para aplicar la nueva configuración de idioma. ¿Reiniciar ahora?")]

NEWLINE = '\n'

ENCODINGS = \
['ascii', 'big5', 'big5hkscs', 'cp037', 'cp273', 'cp424', 'cp437', 'cp500',
 'cp720', 'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856', 'cp857',
 'cp858', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866',
 'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006', 'cp1026',
 'cp1125', 'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255',
 'cp1256', 'cp1257', 'cp1258', 'cp65001', 'euc_jp', 'euc_jis_2004', 'euc_jisx0213',
 'euc_kr', 'gb2312', 'gbk', 'gb18030', 'hz', 'iso2022_jp', 'iso2022_jp_1',
 'iso2022_jp_2', 'iso2022_jp_2004', 'iso2022_jp_3', 'iso2022_jp_ext',
 'iso2022_kr', 'latin_1', 'iso8859_2', 'iso8859_3', 'iso8859_4', 'iso8859_5',
 'iso8859_6', 'iso8859_7', 'iso8859_8', 'iso8859_9', 'iso8859_10', 'iso8859_11',
 'iso8859_13', 'iso8859_14', 'iso8859_15', 'iso8859_16', 'johab', 'koi8_r',
 'koi8_t', 'koi8_u', 'kz1048', 'mac_cyrillic', 'mac_greek', 'mac_iceland',
 'mac_latin2', 'mac_roman', 'mac_turkish', 'ptcp154', 'shift_jis', 'shift_jis_2004',
 'shift_jisx0213', 'utf_32', 'utf_32_be', 'utf_32_le', 'utf_16', 'utf_16_be',
 'utf_16_le', 'utf_7', 'utf_8', 'utf_8_sig']

FONT_WEIGHTS = {100: 0, 200: 12, 300: 25, 400: 50, 500: 57, 600: 63, 700: 75, 800: 81, 900: 87}

LINUX_APP_PATH = '~/.local/share/applications/{}.desktop'.format(APP_NAME.lower())
LINUX_MIME_APP = \
"""[Desktop Entry]
Type=Application
Exec={} %u
StartupNotify=true
Terminal=false
MimeType=x-scheme-handler/{}
Name={}"""
LINUX_MIME_TYPES = \
"""<?xml version="1.0"?>
<mime-info xmlns='http://www.freedesktop.org/standards/shared-mime-info'>
  <mime-type type="{}">
    <comment>{}</comment>
    {}
  </mime-type>
</mime-info>"""
LINUX_MIME_XML = f'~/.local/share/applications/{APP_NAME.lower()}-{APP_NAME.lower()}.xml'

MW_DIC_KEY = '71ae1f74-7edb-4683-be03-8e3d7348660d'            # MW Collegiate Dictionary & Audio API key
MW_DIC_HTTP = 'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{}?key={}'
MW_DAILY_REQ = 1000                                        # daily limit, see https://www.dictionaryapi.com/
MW_WORD_URL = 'https://www.merriam-webster.com/dictionary/{}'

YAN_DICT_KEY = 'dict.1.1.20191120T032741Z.d541dffb1a55247b.b090f62ccd320c7e33f8d88eefde8c8e1ea0ba5b'
YAN_DICT_HTTP = 'https://dictionary.yandex.net/api/v1/dicservice.json/lookup?key={}&text={}&lang={}&ui=en'
YAN_DAILY_REQ = 10000

GOOGLE_KEY = 'AIzaSyAcc_B34Mv7Z4UoVuAMYCEiA9n14_SuEjU'        # Google Search JSON API key
GOOGLE_CSE = '012413034625838642915:je3epsydo2r'              # Google CSE identifier
GOOGLE_HTTP = 'https://www.googleapis.com/customsearch/v1?key={}&cx={}&prettyPrint=true&q={}'
GOOGLE_DAILY_REQ = 100                                        # daily limit, see https://developers.google.com/custom-search/v1/overview

GOOGLE_LANG_LR = {'lang_ar': 'Arabic', 'lang_bg': 'Bulgarian', 'lang_ca': 'Catalan', 'lang_cs': 'Czech',
    'lang_da': 'Danish', 'lang_de': 'German', 'lang_el': 'Greek', 'lang_en': 'English',
    'lang_es': 'Spanish', 'lang_et': 'Estonian', 'lang_fi': 'Finnish', 'lang_fr': 'French',
    'lang_hr': 'Croatian', 'lang_hu': 'Hungarian', 'lang_id': 'Indonesian', 'lang_is': 'Icelandic',
    'lang_it': 'Italian', 'lang_iw': 'Hebrew', 'lang_ja': 'Japanese', 'lang_ko': 'Korean',
    'lang_lt': 'Lithuanian', 'lang_lv': 'Latvian', 'lang_nl': 'Dutch', 'lang_no': 'Norwegian',
    'lang_pl': 'Polish', 'lang_pt': 'Portuguese', 'lang_ro': 'Romanian', 'lang_ru': 'Russian',
    'lang_sk': 'Slovak', 'lang_sl': 'Slovenian', 'lang_sr': 'Serbian', 'lang_sv': 'Swedish',
    'lang_tr': 'Turkish', 'lang_zh-CN': 'Chinese (Simplified)', 'lang_zh-TW': 'Chinese (Traditional)'}
GOOGLE_LANG_HL = {'af': 'Afrikaans', 'sq': 'Albanian', 'sm': 'Amharic', 'ar': 'Arabic', 'az': 'Azerbaijani', 'eu': 'Basque', 
    'be': 'Belarusian', 'bn': 'Bengali', 'bh': 'Bihari', 'bs': 'Bosnian', 'bg': 'Bulgarian', 
    'ca': 'Catalan', 'zh-CN': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)', 
    'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'nl': 'Dutch', 'en': 'English', 'eo': 'Esperanto', 
    'et': 'Estonian', 'fo': 'Faroese', 'fi': 'Finnish', 'fr': 'French', 'fy': 'Frisian', 'gl': 'Galician', 
    'ka': 'Georgian', 'de': 'German', 'el': 'Greek', 'gu': 'Gujarati', 'iw': 'Hebrew', 'hi': 'Hindi', 
    'hu': 'Hungarian', 'is': 'Icelandic', 'id': 'Indonesian', 'ia': 'Interlingua', 'ga': 'Irish', 'it': 'Italian', 
    'ja': 'Japanese', 'jw': 'Javanese', 'kn': 'Kannada', 'ko': 'Korean', 'la': 'Latin', 'lv': 'Latvian', 
    'lt': 'Lithuanian', 'mk': 'Macedonian', 'ms': 'Malay', 'ml': 'Malayam', 'mt': 'Maltese', 'mr': 'Marathi', 
    'ne': 'Nepali', 'no': 'Norwegian', 'nn': 'Norwegian (Nynorsk)', 'oc': 'Occitan', 'fa': 'Persian', 
    'pl': 'Polish', 'pt-BR': 'Portuguese (Brazil)', 'pt-PT': 'Portuguese (Portugal)', 'pa': 'Punjabi', 
    'ro': 'Romanian', 'ru': 'Russian', 'gd': 'Scots Gaelic', 'sr': 'Serbian', 'si': 'Sinhalese', 
    'sk': 'Slovak', 'sl': 'Slovenian', 'es': 'Spanish', 'su': 'Sudanese', 'sw': 'Swahili', 'sv': 'Swedish', 
    'tl': 'Tagalog', 'ta': 'Tamil', 'te': 'Telugu', 'th': 'Thai', 'ti': 'Tigrinya', 'tr': 'Turkish', 
    'uk': 'Ukrainian', 'ur': 'Urdu', 'uz': 'Uzbek', 'vi': 'Vietnamese', 'cy': 'Welsh', 'xh': 'Xhosa', 'zu': 'Zulu'}
GOOGLE_COUNTRIES_CR = {'countryAF': 'Afghanistan', 'countryAL': 'Albania', 'countryDZ': 'Algeria',
    'countryAS': 'American Samoa', 'countryAD': 'Andorra', 'countryAO': 'Angola',
    'countryAI': 'Anguilla', 'countryAQ': 'Antarctica', 'countryAG': 'Antigua and Barbuda',
    'countryAR': 'Argentina', 'countryAM': 'Armenia', 'countryAW': 'Aruba',
    'countryAU': 'Australia', 'countryAT': 'Austria', 'countryAZ': 'Azerbaijan',
    'countryBS': 'Bahamas', 'countryBH': 'Bahrain', 'countryBD': 'Bangladesh',
    'countryBB': 'Barbados', 'countryBY': 'Belarus', 'countryBE': 'Belgium',
    'countryBZ': 'Belize', 'countryBJ': 'Benin', 'countryBM': 'Bermuda',
    'countryBT': 'Bhutan', 'countryBO': 'Bolivia', 'countryBA': 'Bosnia and Herzegovina',
    'countryBW': 'Botswana', 'countryBV': 'Bouvet Island', 'countryBR': 'Brazil',
    'countryIO': 'British Indian Ocean Territory', 'countryBN': 'Brunei Darussalam', 'countryBG': 'Bulgaria',
    'countryBF': 'Burkina Faso', 'countryBI': 'Burundi', 'countryKH': 'Cambodia',
    'countryCM': 'Cameroon', 'countryCA': 'Canada', 'countryCV': 'Cape Verde',
    'countryKY': 'Cayman Islands', 'countryCF': 'Central African Republic', 'countryTD': 'Chad',
    'countryCL': 'Chile', 'countryCN': 'China', 'countryCX': 'Christmas Island',
    'countryCC': 'Cocos (Keeling) Islands', 'countryCO': 'Colombia', 'countryKM': 'Comoros',
    'countryCG': 'Congo', 'countryCD': 'Congo, the Democratic Republic of the', 'countryCK': 'Cook Islands',
    'countryCR': 'Costa Rica', 'countryCI': "Cote D'ivoire", 'countryHR': 'Croatia (Hrvatska)',
    'countryCU': 'Cuba', 'countryCY': 'Cyprus', 'countryCZ': 'Czech Republic',
    'countryDK': 'Denmark', 'countryDJ': 'Djibouti', 'countryDM': 'Dominica',
    'countryDO': 'Dominican Republic', 'countryTP': 'East Timor', 'countryEC': 'Ecuador',
    'countryEG': 'Egypt', 'countrySV': 'El Salvador', 'countryGQ': 'Equatorial Guinea',
    'countryER': 'Eritrea', 'countryEE': 'Estonia', 'countryET': 'Ethiopia',
    'countryEU': 'European Union', 'countryFK': 'Falkland Islands (Malvinas)', 'countryFO': 'Faroe Islands',
    'countryFJ': 'Fiji', 'countryFI': 'Finland', 'countryFR': 'France',
    'countryFX': 'France, Metropolitan', 'countryGF': 'French Guiana', 'countryPF': 'French Polynesia',
    'countryTF': 'French Southern Territories', 'countryGA': 'Gabon', 'countryGM': 'Gambia',
    'countryGE': 'Georgia', 'countryDE': 'Germany', 'countryGH': 'Ghana',
    'countryGI': 'Gibraltar', 'countryGR': 'Greece', 'countryGL': 'Greenland',
    'countryGD': 'Grenada', 'countryGP': 'Guadeloupe', 'countryGU': 'Guam',
    'countryGT': 'Guatemala', 'countryGN': 'Guinea', 'countryGW': 'Guinea-Bissau',
    'countryGY': 'Guyana', 'countryHT': 'Haiti', 'countryHM': 'Heard Island and Mcdonald Islands',
    'countryVA': 'Holy See (Vatican City State)','countryHN': 'Honduras',
    'countryHK': 'Hong Kong', 'countryHU': 'Hungary', 'countryIS': 'Iceland',
    'countryIN': 'India', 'countryID': 'Indonesia', 'countryIR': 'Iran, Islamic Republic of',
    'countryIQ': 'Iraq', 'countryIE': 'Ireland', 'countryIL': 'Israel',
    'countryIT': 'Italy', 'countryJM': 'Jamaica', 'countryJP': 'Japan',
    'countryJO': 'Jordan', 'countryKZ': 'Kazakhstan', 'countryKE': 'Kenya',
    'countryKI': 'Kiribati', 'countryKP': "Korea, Democratic People's Republic of", 'countryKR': 'Korea, Republic of',
    'countryKW': 'Kuwait', 'countryKG': 'Kyrgyzstan', 'countryLA': "Lao People's Democratic Republic",
    'countryLV': 'Latvia', 'countryLB': 'Lebanon', 'countryLS': 'Lesotho',
    'countryLR': 'Liberia', 'countryLY': 'Libyan Arab Jamahiriya', 'countryLI': 'Liechtenstein',
    'countryLT': 'Lithuania', 'countryLU': 'Luxembourg', 'countryMO': 'Macao',
    'countryMK': 'Macedonia, the Former Yugosalv Republc of', 'countryMG': 'Madagascar',
    'countryMW': 'Malawi', 'countryMY': 'Malaysia', 'countryMV': 'Maldives',
    'countryML': 'Mali', 'countryMT': 'Malta', 'countryMH': 'Marshall Islands',
    'countryMQ': 'Martinique', 'countryMR': 'Mauritania', 'countryMU': 'Mauritius',
    'countryYT': 'Mayotte', 'countryMX': 'Mexico', 'countryFM': 'Micronesia, Federated States of',
    'countryMD': 'Moldova, Republic of', 'countryMC': 'Monaco', 'countryMN': 'Mongolia',
    'countryMS': 'Montserrat', 'countryMA': 'Morocco', 'countryMZ': 'Mozambique',
    'countryMM': 'Myanmar', 'countryNA': 'Namibia', 'countryNR': 'Nauru',
    'countryNP': 'Nepal', 'countryNL': 'Netherlands', 'countryAN': 'Netherlands Antilles',
    'countryNC': 'New Caledonia', 'countryNZ': 'New Zealand', 'countryNI': 'Nicaragua',
    'countryNE': 'Niger', 'countryNG': 'Nigeria', 'countryNU': 'Niue',
    'countryNF': 'Norfolk Island', 'countryMP': 'Northern Mariana Islands', 'countryNO': 'Norway',
    'countryOM': 'Oman', 'countryPK': 'Pakistan', 'countryPW': 'Palau',
    'countryPS': 'Palestinian Territory', 'countryPA': 'Panama', 'countryPG': 'Papua New Guinea',
    'countryPY': 'Paraguay', 'countryPE': 'Peru', 'countryPH': 'Philippines',
    'countryPN': 'Pitcairn', 'countryPL': 'Poland', 'countryPT': 'Portugal',
    'countryPR': 'Puerto Rico', 'countryQA': 'Qatar', 'countryRE': 'Reunion',
    'countryRO': 'Romania', 'countryRU': 'Russian Federation', 'countryRW': 'Rwanda',
    'countrySH': 'Saint Helena', 'countryKN': 'Saint Kitts and Nevis', 'countryLC': 'Saint Lucia',
    'countryPM': 'Saint Pierre and Miquelon', 'countryVC': 'Saint Vincent and the Grenadines', 'countryWS': 'Samoa',
    'countrySM': 'San Marino', 'countryST': 'Sao Tome and Principe', 'countrySA': 'Saudi Arabia',
    'countrySN': 'Senegal', 'countryCS': 'Serbia and Montenegro', 'countrySC': 'Seychelles',
    'countrySL': 'Sierra Leone', 'countrySG': 'Singapore', 'countrySK': 'Slovakia',
    'countrySI': 'Slovenia', 'countrySB': 'Solomon Islands', 'countrySO': 'Somalia',
    'countryZA': 'South Africa', 'countryGS': 'South Georgia and the South Sandwich Islands', 'countryES': 'Spain',
    'countryLK': 'Sri Lanka', 'countrySD': 'Sudan', 'countrySR': 'Suriname',
    'countrySJ': 'Svalbard and Jan Mayen', 'countrySZ': 'Swaziland', 'countrySE': 'Sweden',
    'countryCH': 'Switzerland', 'countrySY': 'Syrian Arab Republic', 'countryTW': 'Taiwan, Province of China',
    'countryTJ': 'Tajikistan', 'countryTZ': 'Tanzania, United Republic of', 'countryTH': 'Thailand',
    'countryTG': 'Togo', 'countryTK': 'Tokelau', 'countryTO': 'Tonga',
    'countryTT': 'Trinidad and Tobago', 'countryTN': 'Tunisia', 'countryTR': 'Turkey',
    'countryTM': 'Turkmenistan', 'countryTC': 'Turks and Caicos Islands', 'countryTV': 'Tuvalu',
    'countryUG': 'Uganda', 'countryUA': 'Ukraine', 'countryAE': 'United Arab Emirates',
    'countryUK': 'United Kingdom', 'countryUS': 'United States', 'countryUM': 'United States Minor Outlying Islands',
    'countryUY': 'Uruguay', 'countryUZ': 'Uzbekistan', 'countryVU': 'Vanuatu',
    'countryVE': 'Venezuela', 'countryVN': 'Vietnam', 'countryVG': 'Virgin Islands, British',
    'countryVI': 'Virgin Islands, U.S.', 'countryWF': 'Wallis and Futuna', 'countryEH': 'Western Sahara',
    'countryYE': 'Yemen', 'countryYU': 'Yugoslavia', 'countryZM': 'Zambia', 'countryZW': 'Zimbabwe'}
GOOGLE_COUNTRIES_GL = {'af': 'Afghanistan', 'al': 'Albania', 'dz': 'Algeria', 'as': 'American Samoa', 'ad': 'Andorra', 
    'ao': 'Angola', 'ai': 'Anguilla', 'aq': 'Antarctica', 'ag': 'Antigua and Barbuda', 
    'ar': 'Argentina', 'am': 'Armenia', 'aw': 'Aruba', 'au': 'Australia', 'at': 'Austria', 
    'az': 'Azerbaijan', 'bs': 'Bahamas', 'bh': 'Bahrain', 'bd': 'Bangladesh', 'bb': 'Barbados', 
    'by': 'Belarus', 'be': 'Belgium', 'bz': 'Belize', 'bj': 'Benin', 'bm': 'Bermuda', 'bt': 'Bhutan', 
    'bo': 'Bolivia', 'ba': 'Bosnia and Herzegovina', 'bw': 'Botswana', 'bv': 'Bouvet Island', 'br': 'Brazil', 
    'io': 'British Indian Ocean Territory', 'bn': 'Brunei Darussalam', 'bg': 'Bulgaria', 'bf': 'Burkina Faso', 
    'bi': 'Burundi', 'kh': 'Cambodia', 'cm': 'Cameroon', 'ca': 'Canada', 'cv': 'Cape Verde', 
    'ky': 'Cayman Islands', 'cf': 'Central African Republic', 'td': 'Chad', 'cl': 'Chile', 
    'cn': 'China', 'cx': 'Christmas Island', 'cc': 'Cocos (Keeling) Islands', 'co': 'Colombia', 
    'km': 'Comoros', 'cg': 'Congo', 'cd': 'Congo, the Democratic Republic of the', 'ck': 'Cook Islands', 
    'cr': 'Costa Rica', 'ci': "Cote D'ivoire", 'hr': 'Croatia', 'cu': 'Cuba', 'cy': 'Cyprus', 
    'cz': 'Czech Republic', 'dk': 'Denmark', 'dj': 'Djibouti', 'dm': 'Dominica', 'do': 'Dominican Republic', 
    'ec': 'Ecuador', 'eg': 'Egypt', 'sv': 'El Salvador', 'gq': 'Equatorial Guinea', 'er': 'Eritrea', 
    'ee': 'Estonia', 'et': 'Ethiopia', 'fk': 'Falkland Islands (Malvinas)', 'fo': 'Faroe Islands', 
    'fj': 'Fiji', 'fi': 'Finland', 'fr': 'France', 'gf': 'French Guiana', 'pf': 'French Polynesia', 
    'tf': 'French Southern Territories', 'ga': 'Gabon', 'gm': 'Gambia', 'ge': 'Georgia', 
    'de': 'Germany', 'gh': 'Ghana', 'gi': 'Gibraltar', 'gr': 'Greece', 'gl': 'Greenland', 
    'gd': 'Grenada', 'gp': 'Guadeloupe', 'gu': 'Guam', 'gt': 'Guatemala', 'gn': 'Guinea', 
    'gw': 'Guinea-Bissau', 'gy': 'Guyana', 'ht': 'Haiti', 'hm': 'Heard Island and Mcdonald Islands', 
    'va': 'Holy See (Vatican City State)', 'hn': 'Honduras', 'hk': 'Hong Kong', 'hu': 'Hungary', 
    'is': 'Iceland', 'in': 'India', 'id': 'Indonesia', 'ir': 'Iran, Islamic Republic of', 
    'iq': 'Iraq', 'ie': 'Ireland', 'il': 'Israel', 'it': 'Italy', 'jm': 'Jamaica', 'jp': 'Japan', 
    'jo': 'Jordan', 'kz': 'Kazakhstan', 'ke': 'Kenya', 'ki': 'Kiribati', 'kp': "Korea, Democratic People's Republic of", 
    'kr': 'Korea, Republic of', 'kw': 'Kuwait', 'kg': 'Kyrgyzstan', 'la': "Lao People's Democratic Republic", 
    'lv': 'Latvia', 'lb': 'Lebanon', 'ls': 'Lesotho', 'lr': 'Liberia', 'ly': 'Libyan Arab Jamahiriya', 
    'li': 'Liechtenstein', 'lt': 'Lithuania', 'lu': 'Luxembourg', 'mo': 'Macao', 
    'mk': 'Macedonia, the Former Yugosalv Republic of', 'mg': 'Madagascar', 'mw': 'Malawi', 
    'my': 'Malaysia', 'mv': 'Maldives', 'ml': 'Mali', 'mt': 'Malta', 'mh': 'Marshall Islands', 
    'mq': 'Martinique', 'mr': 'Mauritania', 'mu': 'Mauritius', 'yt': 'Mayotte', 'mx': 'Mexico', 
    'fm': 'Micronesia, Federated States of', 'md': 'Moldova, Republic of', 'mc': 'Monaco', 
    'mn': 'Mongolia', 'ms': 'Montserrat', 'ma': 'Morocco', 'mz': 'Mozambique', 'mm': 'Myanmar', 
    'na': 'Namibia', 'nr': 'Nauru', 'np': 'Nepal', 'nl': 'Netherlands', 'an': 'Netherlands Antilles', 
    'nc': 'New Caledonia', 'nz': 'New Zealand', 'ni': 'Nicaragua', 'ne': 'Niger', 'ng': 'Nigeria', 
    'nu': 'Niue', 'nf': 'Norfolk Island', 'mp': 'Northern Mariana Islands', 'no': 'Norway', 
    'om': 'Oman', 'pk': 'Pakistan', 'pw': 'Palau', 'ps': 'Palestinian Territory', 'pa': 'Panama', 
    'pg': 'Papua New Guinea', 'py': 'Paraguay', 'pe': 'Peru', 'ph': 'Philippines', 'pn': 'Pitcairn', 
    'pl': 'Poland', 'pt': 'Portugal', 'pr': 'Puerto Rico', 'qa': 'Qatar', 're': 'Reunion', 'ro': 'Romania', 
    'ru': 'Russian Federation', 'rw': 'Rwanda', 'sh': 'Saint Helena', 'kn': 'Saint Kitts and Nevis', 
    'lc': 'Saint Lucia', 'pm': 'Saint Pierre and Miquelon', 'vc': 'Saint Vincent and the Grenadines', 
    'ws': 'Samoa', 'sm': 'San Marino', 'st': 'Sao Tome and Principe', 'sa': 'Saudi Arabia', 'sn': 'Senegal', 
    'cs': 'Serbia and Montenegro', 'sc': 'Seychelles', 'sl': 'Sierra Leone', 'sg': 'Singapore', 
    'sk': 'Slovakia', 'si': 'Slovenia', 'sb': 'Solomon Islands', 'so': 'Somalia', 'za': 'South Africa', 
    'gs': 'South Georgia and the South Sandwich Islands', 'es': 'Spain', 'lk': 'Sri Lanka', 'sd': 'Sudan', 
    'sr': 'Suriname', 'sj': 'Svalbard and Jan Mayen', 'sz': 'Swaziland', 'se': 'Sweden', 'ch': 'Switzerland', 
    'sy': 'Syrian Arab Republic', 'tw': 'Taiwan, Province of China', 'tj': 'Tajikistan', 
    'tz': 'Tanzania, United Republic of', 'th': 'Thailand', 'tl': 'Timor-Leste', 'tg': 'Togo', 
    'tk': 'Tokelau', 'to': 'Tonga', 'tt': 'Trinidad and Tobago', 'tn': 'Tunisia', 'tr': 'Turkey', 
    'tm': 'Turkmenistan', 'tc': 'Turks and Caicos Islands', 'tv': 'Tuvalu', 'ug': 'Uganda', 
    'ua': 'Ukraine', 'ae': 'United Arab Emirates', 'uk': 'United Kingdom', 'us': 'United States', 
    'um': 'United States Minor Outlying Islands', 'uy': 'Uruguay', 'uz': 'Uzbekistan', 'vu': 'Vanuatu', 
    've': 'Venezuela', 'vn': 'Viet Nam', 'vg': 'Virgin Islands, British', 'vi': 'Virgin Islands, U.S.', 
    'wf': 'Wallis and Futuna', 'eh': 'Western Sahara', 'ye': 'Yemen', 'zm': 'Zambia', 'zw': 'Zimbabwe'} 

LANGAPPLIED = False    

def readSettings(settings_file=None, write_defaults_on_error=True):
    """
    Checks if 'settings.pxjson' exists in the main directory.
    If not, creates it with the default settings; otherwise, 
    reads 'settings.pxjson' to the global CWSettings.settings object.
    """
    from guisettings import CWSettings
    if not settings_file or not os.path.isfile(settings_file):
        settings_file = SETTINGS_FILE
    if not CWSettings.validate_file(settings_file) and write_defaults_on_error:
        CWSettings.save_to_file(settings_file)
    else:
        try:
            CWSettings.load_from_file(settings_file)
        except Exception as err:
            print(err)
    return CWSettings.settings

def switch_lang(lang=''):
    global LANGAPPLIED    
    if not lang in ('', 'en', 'ru', 'fr', 'de', 'it', 'es'): return
    if not LANGAPPLIED:
        try:
            gettext.translation('base', make_abspath('./locale'), languages=[lang] if lang else 'en').install()
        except:
            gettext.translation('base', make_abspath('./locale'), languages=['en']).install()
        LANGAPPLIED = True
        #print(LANGAPPLIED)