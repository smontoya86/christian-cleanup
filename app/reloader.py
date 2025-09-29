from werkzeug.debug import DebuggedApplication

class Reloader:
    def __init__(self, app, watch_files):
        self.app = app
        self.watch_files = watch_files

    def run(self):
        DebuggedApplication(self.app, evalex=True)
        self.app.run(host='0.0.0.0', port=5001, debug=True, extra_files=self.watch_files)

