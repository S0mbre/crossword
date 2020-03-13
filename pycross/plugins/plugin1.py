from utils.pluginbase import *

class PxPlug1(PxPluginGeneral):

    @replace
    def on_act_help(self, checked):
        print('hey from plugin 1!')