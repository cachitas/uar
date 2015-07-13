import os
import logging
import threading
import zipfile
import io

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText

import uar
from texthandler import TextHandler


logging.basicConfig(level=logging.DEBUG)


class ZipFileFrame(ttk.LabelFrame):

    def __init__(self, master):
        super().__init__(master, text=' ZIP File: ')
        self.logger = logging.getLogger(__name__)
        self._init_ui()

        self.reset_state()

    def _init_ui(self):
        self.browse_btn = ttk.Button(self,
                                     text='Browse',
                                     command=self._on_browse)
        self.browse_btn.pack(side='top',
                             padx=5, pady=5,
                             ipadx=5, ipady=5,
                             expand=True)

        self.extract_btn = ttk.Button(self,
                                      text='Extract',
                                      command=self._on_extract)
        self.extract_btn.pack(side='top',
                              padx=5, pady=5,
                              ipadx=5, ipady=5,
                              expand=True)

    def _on_browse(self):
        self.logger.debug('Opening a file dialog')
        file_opt = dict(
            defaultextension='.zip',
            filetypes=[('zip files', '.zip')],
            # initialdir='~/Downloads',
            initialdir='.',  # for testing
            initialfile='',
            parent=self.master,
            title='Choose the zipped results',
        )
        filename = filedialog.askopenfilename(**file_opt)

        if filename != '':
            self.logger.info("File '%s' selected", filename)
            self.zipfilename = filename
            self.extract_btn.config(state='normal')
        else:
            self.logger.debug("Dialog canceled")
            self.reset_state()

    def _on_extract(self):
        self.logger.debug('Starting the extraction')

        # Get options values
        gzip_var = self.master.options_frame.gzip_var
        tofolder_var = self.master.options_frame.tofolder_var

        # Inspect zip file and set progressbar maximum value
        self.master.inspect_zipfile()

        # Extract the files
        self.master.extract_nested_zipfile()

    def reset_state(self):
        self.logger.debug("Reset state to initial values")
        self.zipfilename = None
        self.output_dir = None
        self.extract_btn.config(state='disabled')


class OptionsFrame(ttk.LabelFrame):

    def __init__(self, master):
        super().__init__(master, text=' Options: ')
        self.logger = logging.getLogger(__name__)
        self.gzip_var = tk.IntVar(value=1)
        self.tofolder_var = tk.IntVar(value=1)
        self._init_ui()

    def _init_ui(self):
        self.gzip_chb = tk.Checkbutton(self,
                                       text='Decompress .gz images',
                                       variable=self.gzip_var)
        self.gzip_chb.pack(anchor='w', expand=True)

        self.tofolder_chb = tk.Checkbutton(self,
                                           text='Extract item into a folder',
                                           variable=self.tofolder_var)
        self.tofolder_chb.pack(anchor='w', expand=True)


class LoggerFrame(ttk.LabelFrame):

    def __init__(self, master):
        super().__init__(master, text=' Progress: ')
        self.logger = logging.getLogger(__name__)
        self._init_ui()

        text_handler = TextHandler(self.st)
        self.logger.addHandler(text_handler)

    def _init_ui(self):
        self.pb = ttk.Progressbar(self)
        self.pb.pack(padx=5, pady=5,
                     ipadx=5, ipady=5,
                     fill='x', expand=False)

        self.st = ScrolledText(self,
                               state='disabled',
                               font='TkFixedFont',
                               width=8,
                               height=8)
        self.st.pack(padx=5, pady=5,
                     ipadx=5, ipady=5,
                     fill='both', expand=True)


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._init_ui()

        self.progressbar = self.logger_frame.pb

    def _init_ui(self):
        self.logger.debug('Initializing the GUI...')
        self.title('Unzip Alignment Results')
        self.minsize(width=500, height=200)

        self.input_frame = ZipFileFrame(self)
        self.input_frame.grid(column=0, row=0,
                              padx=5, pady=5,
                              ipadx=5, ipady=5,
                              sticky='nsew')

        self.options_frame = OptionsFrame(self)
        self.options_frame.grid(column=1, row=0,
                                padx=5, pady=5,
                                ipadx=5, ipady=5,
                                sticky='nsew')

        self.logger_frame = LoggerFrame(self)
        self.logger_frame.grid(column=0, row=1, columnspan=2,
                               padx=5, pady=5,
                               ipadx=5, ipady=5,
                               sticky='nsew')

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

    def _check_worker_thread(self, thread, logmsg=None,
                             widget=None, widget_config={'state': 'normal'}):
        """Check worker thread status.
        Can also provide a `widget` to enable when thread is done working.
        This is the default, but can be changed with the argument
        `widget_config`.
        """
        if thread.is_alive():
            self.after(500, self._check_worker_thread,
                       thread, logmsg, widget, widget_config)
        else:
            if logmsg is not None:
                self.logger.info(logmsg)
            if widget is not None:
                widget.config(**widget_config)

    def inspect_zipfile(self):
        """Inspect given zip file in order to set the progress bar
        maximum value.
        During this process the progress bar is in indeterminate state.
        """
        zf = self.input_frame.zipfilename
        self.logger.info("Inspecting '%s'", zf)

        self.logger_frame.pb.config(mode='indeterminate')
        self.logger_frame.pb.start()
        inner_zfs = uar.retrieve_inner_zipfiles(zf)
        self.logger_frame.pb.stop()

        self.logger_frame.pb.config(mode='determinate',
                                    value=0,
                                    maximum=len(inner_zfs))

    def extract_nested_zipfile(self):
        """Extract files using `uar` methodology.
        """
        zf = self.input_frame.zipfilename
        pattern = r'_warped\.'
        output_dir = os.path.splitext(zf)[0]
        inner_zipfiles = uar.retrieve_inner_zipfiles(zf)

        def extract_threaded(zf, pattern, inner_zipfiles, output_dir):
            with zipfile.ZipFile(zf, 'r') as zfile:
                for i, name in enumerate(inner_zipfiles):
                    self.logger.info("Extracting '%s'", name)
                    zfiledata = io.BytesIO(zfile.read(name))
                    uar.extract_files(zfiledata, pattern, output_dir)
                    self.logger_frame.pb['value'] = i + 1

        t = threading.Thread(target=extract_threaded,
                             args=(zf, pattern, inner_zipfiles, output_dir))
        t.start()
        self._check_worker_thread(
            t, logmsg="Done. Output is in '{}'".format(output_dir))


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
