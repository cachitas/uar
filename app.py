import logging
import re
import queue

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText

import uar
from texthandler import TextHandler


logger = logging.getLogger(__name__)


class ZipFileFrame(ttk.LabelFrame):

    def __init__(self, master):
        super().__init__(master, text=' ZIP File: ')
        self._init_ui()

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
                                      state='disabled',
                                      command=self._on_extract)
        self.extract_btn.pack(side='top',
                              padx=5, pady=5,
                              ipadx=5, ipady=5,
                              expand=True)

    def _on_browse(self):
        logger.debug('Opening a file dialog')
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
            self.master._reset()
            logger.info("File '%s' selected", filename)
            self.master.zipfilename = filename
            self.extract_btn.config(state='normal')
        else:
            logger.debug("Dialog canceled")
            self.zipfilename = None
            self.extract_btn.config(state='disabled')

    def _on_extract(self):
        logger.debug('Starting the extraction')
        self.master.extract()


class OptionsFrame(ttk.LabelFrame):

    def __init__(self, master):
        super().__init__(master, text=' Options: ')
        self.gzip_var = tk.BooleanVar(value=1)
        self.tofolder_var = tk.BooleanVar(value=1)
        self._init_ui()

    def _init_ui(self):
        self.gzip_chb = tk.Checkbutton(
            self,
            text='Decompress .gz files',
            variable=self.gzip_var
        )
        self.gzip_chb.pack(anchor='w', expand=True)

        self.tofolder_chb = tk.Checkbutton(
            self,
            text='Extract each item into its folder',
            variable=self.tofolder_var
        )
        self.tofolder_chb.pack(anchor='w', expand=True)


class LoggerFrame(ttk.LabelFrame):

    def __init__(self, master):
        super().__init__(master, text=' Progress: ')
        self._init_ui()

        text_handler = TextHandler(self.st)
        logger.addHandler(text_handler)
        uar.logger.addHandler(text_handler)  # shows logging from the module

    def _init_ui(self):
        self.pb = ttk.Progressbar(self, mode='indeterminate')
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
        self._init_ui()

        self.pattern = re.compile(r'_warped\.')
        self.tasks_queue = queue.Queue(maxsize=1)

        self._reset()
        self._process_queue()

    def _init_ui(self):
        logger.debug('Initializing the GUI...')
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

    def _reset(self):
        """Resets all runtime attributes to their initial values.
        It is used to prepare the application to extract another file.
        """
        logger.debug('Resetting application state')
        self.zipfilename = None
        self.extractor = None
        self.logger_frame.pb.config(value=0, mode='determinate')

    def _process_queue(self):
        try:
            # Check if there's a task to do
            task = self.tasks_queue.get(block=False)
        except queue.Empty:
            self.after(100, self._process_queue)
        else:
            # Do the task
            task, kwargs = task
            try:
                getattr(self, task)(**kwargs)
            except AttributeError:
                logger.exception()

            self.tasks_queue.task_done()

            # Check for another task
            self.after(100, self._process_queue)

    def _disable_input_wigets(self):
        """Disable the input widgets.
        This runs when the extraction process starts.
        """
        logger.debug("Disabling 'Input' and 'Options' frames")
        for child in self.input_frame.winfo_children():
            child.config(state='disabled')
        for child in self.options_frame.winfo_children():
            child.config(state='disabled')

    def _config_widget(self, widget, **kwargs):
        """Configure widget.
        This is a wrapper around `tkinter` widget's `.config()` method.
        """
        logger.debug("Configuring '{}': {}".format(widget, kwargs))
        if widget == 'progressbar':
            widget = self.logger_frame.pb
        widget.config(**kwargs)

    def _call_widget_method(self, widget, method, **kwargs):
        logger.debug("Calling '{}.{}(kwargs={})".format(
                     widget, method, kwargs))
        if widget == 'progressbar':
            widget = self.logger_frame.pb
        getattr(widget, method)(**kwargs)

    def _extraction_completed(self):
        logger.debug("Enabling 'Input' and 'Options' frames")
        for child in self.input_frame.winfo_children():
            child.configure(state='normal')
        for child in self.options_frame.winfo_children():
            child.configure(state='normal')
        logger.debug("Disabling 'Extract' button")
        self.input_frame.extract_btn.config(state='disabled')
        logger.debug("Waiting for Thread to finish")
        self.extractor.join()  # Wait for the Thread used to finish
        logger.info("Done!")

    def extract(self):
        """Extract.
        """
        logger.debug("Spawning and starting a new Thread")
        self.extractor = uar.UAR(
            zipfilename=self.zipfilename,
            pattern=self.pattern,
            options={
                'degzip': self.options_frame.gzip_var.get(),
                'tofolder': self.options_frame.tofolder_var.get(),
            },
            tasks_queue=self.tasks_queue,
        )
        self.extractor.start()


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format=('[%(asctime)s.%(msecs)03d]'
                ' [%(threadName)-10s]'
                ' [%(levelname)-5s]'
                ' %(name)s: %(message)s'),
        datefmt='%H:%M:%S'
    )
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
