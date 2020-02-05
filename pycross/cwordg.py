# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross
import os, sys, traceback, argparse

# ******************************************************************************** #

## Main function that creates and launches the application.
def main():

    # parse command-line parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--settings', help='Load settings from file')
    parser.add_argument('-o', '--open', help='Open crossword file')
    parser.add_argument('-n', '--new', action='store_true', help='Create crossword')
    parser.add_argument('--cols', type=int, default=15, help='Number of columns')
    parser.add_argument('--rows', type=int, default=15, help='Number of rows')
    parser.add_argument('--pattern', type=int, default=1, choices=[1, 2, 3, 4], help='Pattern type for new crossword')
    parser.add_argument('-e', '--empty', action='store_true', help='Do not open/restore or create a crossword')
    parser.add_argument('-a', '--addsrc', default='', action='append', help='Add word source') # see WordSrcDialog definition in forms.py for source string format
    args = parser.parse_args()

    from utils.globalvars import readSettings, switch_lang, DEBUGGING

    # read settings      
    if args.settings:
        settings_file = args.settings
    elif args.open and os.path.splitext(args.open)[1][1:].lower() == 'pxjson':
        settings_file = args.open
        args.open = None
    else:
        settings_file = None    
    settings = readSettings(settings_file)
    
    # switch language
    switch_lang(settings['common']['lang']) 

    from PyQt5 import QtWebEngineWidgets
    from gui import QtCore, QtWidgets, MainWindow

    try:        
        # change working dir to current for correct calls to git
        os.chdir(os.path.dirname(os.path.abspath(__file__)))           
        # initialize Qt Core App settings
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        # create QApplication instance
        app = QtWidgets.QApplication(sys.argv)  
        # initialize core web engine settings
        QtWebEngineWidgets.QWebEngineSettings.defaultSettings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.PluginsEnabled, True)
        QtWebEngineWidgets.QWebEngineSettings.defaultSettings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.DnsPrefetchEnabled, True)
        QtWebEngineWidgets.QWebEngineProfile.defaultProfile().setUseForGlobalCertificateVerification()
        # localize Qt widgets
        lang = settings['common']['lang'] or 'en' 
        locale = QtCore.QLocale(lang)
        locale_name = locale.name()
        #print(locale_name)
        QtCore.QLocale.setDefault(locale)
        if lang != 'en':
            qts = ('qtbase_', 'qt_')
            for qt in qts:
                translator = QtCore.QTranslator()
                if translator.load(locale, qt, '', f"locale/{locale_name}/qt"):
                    if not app.installTranslator(translator) and DEBUGGING:
                        print(_("Cannot install QT translator for locale '{}' and domain '{}'!").format(locale_name, qt))
        # create main window (passing all found command-line args)
        MainWindow(**vars(args))        
        # run app's event loop
        sys.exit(app.exec())
                
    except SystemExit as err:        
        if str(err) != '0':
            traceback.print_exc(limit=None)
        
    except Exception as err:
        traceback.print_exc(limit=None)     
        sys.exit(1)
        
    except:
        traceback.print_exc(limit=None)
        sys.exit(1)
    
# ******************************************************************************** #

## Program entry point.
if __name__ == '__main__':  
    main() 
