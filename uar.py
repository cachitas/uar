import gzip
import io
import os
import re
import shutil
import zipfile

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk


class UAR(tk.Tk):

    def __init__(self, parent):

        tk.Tk.__init__(self, parent)
        self.parent = parent

        self.zip_filename = tk.StringVar(value='')
        self.output_dir = tk.StringVar(value='')
        self.gzip_var = tk.IntVar(value=1)
        self.status_msg = tk.StringVar(value='')

        self.initialize()

    def initialize(self):
        """Initialize the GUI.
        """
        self.title('Unzip Alignment Results')
        self.minsize(width=600, height=50)

        self.grid()

        self.open_btn = tk.Button(self, text='Select ZIP',
                                  command=self.askopenfilename)
        self.open_btn.grid(column=0, row=0, sticky='WE', padx=5, pady=5)

        self.open_ent = tk.Entry(self, textvariable=self.zip_filename,
                                 state='readonly', relief='flat')
        self.open_ent.grid(column=1, row=0, sticky='WE', padx=5, pady=5)

        self.output_lbl = tk.Label(self, text='Output Location:')
        self.output_lbl.grid(column=0, row=1, sticky='E', padx=5, pady=5)

        self.output_ent = tk.Entry(self, textvariable=self.output_dir,
                                   state='readonly', relief='flat')
        self.output_ent.grid(column=1, row=1, sticky='WE', padx=5, pady=5)

        self.options_lbl = tk.Label(self, text='Options:')
        self.options_lbl.grid(column=0, row=2, sticky='E', padx=5, pady=5)

        self.opt_gzip_chb = tk.Checkbutton(self,
                                           text='Uncompress .gz images',
                                           variable=self.gzip_var)
        self.opt_gzip_chb.grid(column=1, row=2, sticky='W')

        self.extract_btn = tk.Button(self, text='Extract images',
                                     state='disabled',
                                     command=self.extract_images)
        self.extract_btn.grid(column=0, row=3, sticky='WE', padx=5, pady=5)

        self.extract_progbar = ttk.Progressbar(self, orient='horizontal',
                                               length=150, mode='determinate')
        self.extract_progbar.grid(column=1, row=3, sticky='WE', padx=5, pady=5)

        self.statusbar = tk.Entry(self, textvariable=self.status_msg,
                                  state='readonly', relief='flat')
        self.statusbar.grid(column=0, row=4, columnspan=2, sticky='WE',
                            padx=5, pady=5)

        self.grid_columnconfigure(1, weight=1)
        self.resizable(True, False)

    def askopenfilename(self):
        """Returns the name of the file chosen.
        """
        file_opt = {}
        file_opt['defaultextension'] = '.zip'
        file_opt['filetypes'] = [('zip files', '.zip'), ('all files', '.*')]
        file_opt['initialdir'] = '~/Downloads'
        file_opt['initialfile'] = ''
        file_opt['parent'] = self.parent
        file_opt['title'] = 'Choose the zipped results'

        filename = filedialog.askopenfilename(**file_opt)

        if filename != '':
            self.zip_filename.set(filename)
            self.extract_btn.config(state='normal')

            # create a folder named as the zip file to extract into
            self.output_dir.set(os.path.splitext(self.zip_filename.get())[0])
            if not os.path.exists(self.output_dir.get()):
                os.mkdir(self.output_dir.get())
        else:
            self.extract_btn.config(state='disabled')

    def extract_images(self):
        """Extract images.
        """

        # inspect the main zip file to account for inner ones
        files_to_extract = []
        self.status_msg.set('Inspecting...')
        self.update_idletasks()
        with zipfile.ZipFile(self.zip_filename.get(), 'r') as zfile:
            for name in zfile.namelist():
                if re.search(r'\.zip$', name, flags=re.IGNORECASE) != None:
                    files_to_extract.append(name)

        self.extract_progbar['value'] = 0
        self.extract_progbar['maximum'] = len(files_to_extract)

        with zipfile.ZipFile(self.zip_filename.get(), 'r') as zfile:
            for i, name in enumerate(files_to_extract):
                self.status_msg.set('Unzipping {}'.format(
                    os.path.basename(name)))

                zfiledata = io.BytesIO(zfile.read(name))
                with zipfile.ZipFile(zfiledata) as zfile2:
                    for name2 in zfile2.namelist():
                        filename = os.path.basename(name2)

                        # skip directories
                        if not filename:
                            continue

                        # filter files: only want those having 'wraped'
                        if re.search(r'_warped\.', name2) is None:
                            continue

                        # copy file (taken from zipfile's extract)
                        source = zfile2.open(name2)
                        target = open(os.path.join(
                            self.output_dir.get(), filename), "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)

                        # uncompress the image if asked to
                        if self.gzip_var.get() == 1:
                            self.uncompress_gzipped_file(target)

                self.extract_progbar["value"] = i + 1
                self.update_idletasks()
            else:
                self.status_msg.set('Done')

    @staticmethod
    def uncompress_gzipped_file(file_obj):
        assert file_obj.name.endswith('.gz')
        source = gzip.open(file_obj.name, 'rb')
        target = open(source.name[:-3], 'wb')
        with source, target:
            target.write(source.read())
        os.remove(source.name)


def main():
    app = UAR(None)
    app.mainloop()


if __name__ == '__main__':
    main()
