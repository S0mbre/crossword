from utils.api import *

class PxPlug1(PxPluginGeneral):

    @after
    def initUI(self, autoloadcw=True):
        print('hey!')