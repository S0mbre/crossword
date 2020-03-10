from utils.api import *

class PxPlug2(PxPluginBase):
    def test(self):
        self.mainwin.trigger_action('act_config', False)