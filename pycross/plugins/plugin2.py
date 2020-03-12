from utils.api import *

class PxPlug2(PxPluginGeneral):
    def test(self):
        self.mainwin.trigger_action('act_config', False)