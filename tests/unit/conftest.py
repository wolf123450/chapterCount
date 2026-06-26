import sys
import types

# Stub out calibre module before importing any test files
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
