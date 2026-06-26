try:
    from calibre.customize import InterfaceActionBase
except ImportError:
    class InterfaceActionBase:
        pass


class ChapterCountPlugin(InterfaceActionBase):
    name                    = 'Chapter Count'
    description             = 'Count chapters in ebooks and store in custom columns'
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'Your Name'
    version                 = (0, 1, 0)
    minimum_calibre_version = (5, 0, 0)
    actual_plugin           = 'calibre_plugins.chapter_count.action:ChapterCountAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.chapter_count.ui.preferences_widget import PreferencesWidget
        return PreferencesWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
