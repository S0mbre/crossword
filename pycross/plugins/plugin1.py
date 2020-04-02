from utils.pluginbase import *

class PxPlugin1(PxPluginGeneral):

    @before
    def leaveEvent(self, event: PyQt5.QtCore.QEvent):
        # @brief Fires when the mouse leaves the main window.
        # Default implementation here as a placeholder for possible overrides in custom plugins.
        # @param event `QtCore.QEvent` the handled event
        print('!')