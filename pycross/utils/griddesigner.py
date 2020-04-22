# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.griddesigner
from .globalvars import *
from PyQt5 import QtGui, QtCore, QtWidgets
from PIL import Image

# ******************************************************************************** #
# *****          ImgPixelator
# ******************************************************************************** # 

"""
# Open Paddington
img = Image.open("paddington.png")

# Resize smoothly down to 16x16 pixels
imgSmall = img.resize((16,16),resample=Image.BILINEAR)

# Scale back up using NEAREST to original size
result = imgSmall.resize(img.size,Image.NEAREST)

# Save
result.save('result.png')
"""

## @brief
class ImgPixelator(QtWidgets.QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.lo_main = QtWidgets.QVBoxLayout()
        self.lo_center = QtWidgets.QHBoxLayout()
        self.splitter1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.l_img = QtWidgets.QLabel()