# -*- coding: utf-8 -*-
"""
Created on Tue Oct 22 11:38:25 2019

@author: iskander.shafikov
"""

from utils.utils import *
import sys
import traceback
from gui import QtWidgets, MainWindow

## ******************************************************************************** ##

def main():
    
    try:
        app = QtWidgets.QApplication(sys.argv)
        gui = MainWindow()
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