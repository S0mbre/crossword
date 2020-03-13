from utils.pluginbase import *

class PxPlug2(PxPluginGeneral):

    @after
    def on_act_help(self, checked):
        print('hey from plugin 2!')