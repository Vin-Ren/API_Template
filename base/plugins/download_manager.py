import os


from .base import BasePlugin
from ..data_structs import ProgressInfo, Timer
from ..helper.snippets import metric_size_formatter, make_progress_bar, dict_updater


class DownloadFileHandler:
    TEMPORARY_DIR = 'temp'
    TEMPORARY_EXTENSION = 'tmp'
    CHUNK_SIZE = 512
    
    def __getattribute__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return getattr(self.handler, name)
    
    def __init__(self, filename):
        self.filename = filename
        self.temporary_filename = os.path.join(self.__class__.TEMPORARY_DIR, filename, self.__class__.TEMPORARY_EXTENSION)
        self.temp_handler = open(self.temporary_filename, 'wb')
        
        if len(self.__class__.TEMPORARY_DIR) > 0:
            try:
                os.makedirs(self.__class__.TEMPORARY_DIR)
            except:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            self.finalize()
        else:
            self.drop()
    
    def finalize(self):
        self.temp_handler.flush()
        self.temp_handler.close()
        with open(self.temporary_filename, 'rb') as src_file:
            with open(self.filename, 'wb') as dest_file:
                while True:
                    content = src_file.read(self.CHUNK_SIZE)
                    if len(content) <= 0:
                        break
                    dest_file.write(content)
    
    def drop(self):
        os.remove(os.path.join(os.path.abspath(), self.TEMPORARY_DIR, self.temporary_filename))


class DownloadManager(BasePlugin):
    DOWNLOAD_CHUNK_SIZE = 512
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.session_kwargs = {'stream':True}
        
        self.predownload_hooks = []
        self.progress_hooks = []
        self.finished_hooks = []
    
    def register_defaults(self):
        self.register_predownload_hook(self.default_predownload_hook)
        self.register_prog_hook(self.default_prog_hook)
        self.register_finished_hook(self.default_finished_hook)
        return self
    
    def register_predownload_hook(self, hook):
        self.progress_hooks.append(hook)
        return self
    
    def register_prog_hook(self, hook):
        self.progress_hooks.append(hook)
        return self
    
    def register_finished_hook(self, hook):
        self.finished_hooks.append(hook)
        return self
    
    def default_predownload_hook(self, progress: ProgressInfo):
        progress.content_length = progress.stream.headers['Content-Length']
    
    def default_prog_hook(self, progress: ProgressInfo):
        suffix = " | {curr} of {max}    {speed} ({elapsed_time}s)"
        suffix = suffix.format(curr=metric_size_formatter(progress.pipe_handler.tell()), max=metric_size_formatter(progress.content_length), 
                                speed=metric_size_formatter(round(progress.pipe_handler.tell()/progress.time_info.elapsed, 2), suffix='bps'), elapsed_time=round(progress.time_info.elapsed,2))
        print(make_progress_bar(progress.pipe_handler.tell(), length=self.config.download_progress_bar_length, vmax=progress.content_length, suffix=suffix), end=' '*5)
    
    def default_finished_hook(self, progress: ProgressInfo):
        print("Downloaded file in %ds" % round(progress.time_info.duration, 2))
    
    def download_to_file(self, filename, *session_args, retry_download=True, progress_info_updater=None, **session_kwargs):
        timer = Timer().start()
        session_kwargs = dict_updater(self.session_kwargs, session_kwargs)
        
        with self.session.get(*session_args, **session_kwargs) as stream, DownloadFileHandler(filename) as file_handler:
            prog_info = ProgressInfo(stream=stream, pipe_handler=file_handler, time_info=timer)
            prog_info.update(progress_info_updater) if progress_info_updater is not None else None
            [hook(prog_info) for hook in self.predownload_hooks]
            for chunk in stream.iter_content(self.DOWNLOAD_CHUNK_SIZE):
                if not chunk:
                    break
                file_handler.write(chunk)

                timer.update_current()
                [hook(prog_info) for hook in self.progress_hooks]
            timer.end()
        [hook(prog_info) for hook in self.finished_hooks]
        
        if stream.ok:
            return prog_info
        if retry_download:
            return self.download_to_file(filename, *session_args, retry_download=retry_download, **session_kwargs)
