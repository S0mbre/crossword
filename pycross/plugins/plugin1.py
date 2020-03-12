from utils.api import *

class PxPlug1(PxPluginGeneral):

    @after
    def on_act_help(self, checked):
        print('hey!')