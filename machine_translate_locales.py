# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## Uses Google Translate to automatically translate the POT files 
# located in pycross/locale folder.
import os
import polib
import googletrans
import time
from multiprocessing import Pool

LOCALEDIR = os.path.join(os.path.dirname(__file__), 'pycross', 'locale')
SRC_LANG = 'en'
EXCLUDED_LANGS = ('en', 'ru')
# ***************************************************************** #

def translate_pot(src_file, lang):
    logfile = os.path.join(os.path.dirname(src_file), 'log.txt')
    translator = googletrans.Translator()
    with open(logfile, 'w', encoding='utf-8') as lfile:
        n = 0
        L = 0
        try:
            print(f'TRANSLATING {src_file} from {SRC_LANG} into {lang}...', 
                    file=lfile, flush=True)
            po = polib.pofile(src_file)
            untranslated = po.untranslated_entries()
            L = len(untranslated)
            if L == 0:
                print('No untranslated entries found!', file=lfile, flush=True)
                return 100.0
            print(f"Found {L} untranslated entries ({100. - po.percent_translated():.0f}% of total)", 
                    file=lfile, flush=True)            
            for entry in untranslated:
                try:                    
                    entry.msgstr = translator.translate(entry.msgid, src=SRC_LANG, dest=lang).text
                    n += 1
                except Exception as errr:
                    print(f"Pair {n}/{L}: {errr}", file=lfile, flush=True)                    
                    po.save()
                    po.save_as_mofile('base.mo')
                    return 100. - po.percent_translated()
            po.save()
            po.save_as_mofile('base.mo')
            return 100. - po.percent_translated()
        except Exception as err:
            print(err, file=lfile, flush=True)
            return 0.0

def main():
    langs = googletrans.LANGUAGES.keys()
    pot_files = []
    with os.scandir(LOCALEDIR) as it:
        for entry in it:
            if not entry.is_dir(): continue
            lang = entry.name[:2].lower()
            if (not lang in langs) or (lang in EXCLUDED_LANGS): continue
            print(f"Language folder detected: {googletrans.LANGUAGES[lang]}")
            pot_file = os.path.join(entry.path, 'LC_MESSAGES', 'base.po')
            if not os.path.isfile(pot_file):
                print(f"File '{pot_file}' does not exist! Skipping...")
                continue
            pot_files.append((pot_file, lang))
    print('')
    if pot_files:
        pool = Pool(len(pot_files))
        results = zip(pot_files, list(pool.starmap(translate_pot, pot_files)))
        for r in results:
            print(f"{googletrans.LANGUAGES[r[0][1]]}: {r[1]:.0f}% translated")
    else:
        print('No POT files found!')

# ***************************************************************** #

if __name__ == '__main__':  
    main() 