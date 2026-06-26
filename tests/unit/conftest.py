# Calibre stubs set up in root conftest, but also set here for safety
import sys
import types

if 'calibre' not in sys.modules:
    calibre = types.ModuleType('calibre')
    calibre_customize = types.ModuleType('calibre.customize')
    calibre_utils = types.ModuleType('calibre.utils')
    calibre_config = types.ModuleType('calibre.utils.config')

    class InterfaceActionBase:
        pass

    calibre_config.JSONConfig = dict
    calibre.customize = calibre_customize
    calibre.utils = calibre_utils
    calibre_utils.config = calibre_config
    calibre_customize.InterfaceActionBase = InterfaceActionBase

    sys.modules['calibre'] = calibre
    sys.modules['calibre.customize'] = calibre_customize
    sys.modules['calibre.utils'] = calibre_utils
    sys.modules['calibre.utils.config'] = calibre_config

# EPUB fixtures added in Task 4
