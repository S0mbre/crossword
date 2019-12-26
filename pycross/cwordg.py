# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

import os, sys, traceback
from gui import QtWidgets, MainWindow

from utils.onlineservices import Cloudstorage

## ******************************************************************************** ##

def main():
    
    try:
        # change working dir to current for correct calls to git
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        app = QtWidgets.QApplication(sys.argv)
        MainWindow()

        settings = {'account': '', 'bearer_token': '', 'root_folder': '', 'user': ''}  
        cloud = Cloudstorage(settings)
        print(f"User = {settings['user']}")
        print(cloud._get_quota())

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
    
## ******************************************************************************** ##

if __name__ == '__main__':  
    main() 
