from calibre.gui2.actions import InterfaceAction


class ChapterCountAction(InterfaceAction):
    name        = 'Chapter Count'
    action_spec = ('Chapter Count', None, 'Count chapters in selected books', None)

    def genesis(self):
        self.qaction.triggered.connect(self.count_selected)

    def initialization_complete(self):
        pass

    def count_selected(self):
        pass
