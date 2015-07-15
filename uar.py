"""
UAR - Unzip Alignment Results
=============================
"""

import gzip
import io
import logging
import os
import re
import shutil
import threading
import time
import zipfile

logger = logging.getLogger(__name__)


class UAR(threading.Thread):

    def __init__(self, zipfilename, pattern, options, tasks_queue):
        super().__init__()
        self.zipfilename = zipfilename
        self.pattern = pattern
        self.options = options
        self.tasks_queue = tasks_queue

    def run(self):

        # When task starts running we send a signal to disable all
        # other widgets in orther to prevent user input
        self.tasks_queue.put(
            ('_disable_input_wigets', dict())
        )

        # Change the progressbar to indeterminate mode to inspect the
        # selected file and to create the output directory
        self.tasks_queue.put(
            ('_config_widget', dict(widget='progressbar',
                                    mode='indeterminate',
                                    maximum=10))
        )
        self.tasks_queue.put(
            ('_call_widget_method', dict(widget='progressbar', method='start'))
        )

        # Look for the output directory.
        output_dir = os.path.splitext(self.zipfilename)[0]
        prepare_output_dir(output_dir)

        # Inspect the zipfile given and collect the inner ones
        inner_zipfiles = retrieve_inner_zipfiles(self.zipfilename)

        # Revert the progressbar to determinate mode and set its maximum value
        number_of_tasks = len(inner_zipfiles) + 1
        if self.options['degzip'] == 1:
            number_of_tasks += 1
        if self.options['tofolder'] == 1:
            number_of_tasks += 1
        self.tasks_queue.put(
            ('_call_widget_method', dict(widget='progressbar', method='stop'))
        )
        self.tasks_queue.put(
            ('_config_widget', dict(widget='progressbar',
                                    mode='determinate',
                                    value=0,
                                    maximum=number_of_tasks))
        )

        # Extract the files
        with zipfile.ZipFile(self.zipfilename, 'r') as zfile:
            for i, name in enumerate(inner_zipfiles):
                logger.info("Extracting '%s'", name)
                zfiledata = io.BytesIO(zfile.read(name))
                extract_files(zfiledata, self.pattern, output_dir)
                time.sleep(.5)
                self.tasks_queue.put(
                    ('_call_widget_method', dict(widget='progressbar',
                                                 method='step'))
                )

        if self.options['degzip'] == 1:
            decompress_gzipped_files(output_dir)
            logger.info("Decompressed gzipped files")
            self.tasks_queue.put(
                ('_call_widget_method', dict(widget='progressbar',
                                             method='step'))
            )

        if self.options['tofolder'] == 1:
            move_files_inside_folders(output_dir)
            logger.info("Extracted files placed in their own folder")
            self.tasks_queue.put(
                ('_call_widget_method', dict(widget='progressbar',
                                             method='step'))
            )

        logger.info("All files extracted to '{}'".format(output_dir))

        self.tasks_queue.put(
            ('_extraction_completed', dict())
        )

        # Need to explicitly set the last value. step() can't do it
        self.tasks_queue.put(
            ('_config_widget', dict(widget='progressbar',
                                    value=number_of_tasks))
        )


def extract_nested_zips(zipfilename, pattern):
    """Extract nested zipped files.

    Extracts desired files from within zipped files inside the given
    zipped file.

    The files extracted are placed inside a folder named after the
    provided zipped file.
    """

    output_dir = os.path.splitext(zipfilename)[0]
    prepare_output_dir(output_dir)

    inner_zipfiles = retrieve_inner_zipfiles(zipfilename)

    with zipfile.ZipFile(zipfilename, 'r') as zfile:
        for i, name in enumerate(inner_zipfiles):
            zfiledata = io.BytesIO(zfile.read(name))

            extract_files(zfiledata, pattern, output_dir)


def prepare_output_dir(output_dir):
    """Create output directory.
    If one directory with the same name already exists, remove it
    and create again. There may be a better way to do this...
    """
    try:
        logger.debug("Creating output directory '{}'".format(output_dir))
        os.mkdir(output_dir)
    except OSError:
        logger.debug("Output directory already exists."
                     " Removing '{}'".format(output_dir))
        shutil.rmtree(output_dir)
        time.sleep(.5)  # wait for the IO operations to complete
        prepare_output_dir(output_dir)
    else:
        logger.debug("Output directory created '{}'".format(output_dir))
    finally:
        time.sleep(.5)  # wait for the IO operations to complete


def retrieve_inner_zipfiles(zipfilename):
    """Inspect the given zipped file and retrieve the inner ones.
    """

    inner_zipfiles = []

    logger.debug('Looking for zipped files inside {}'.format(zipfilename))
    with zipfile.ZipFile(zipfilename, 'r') as zfile:
        for name in zfile.namelist():
            if re.search(r'\.zip$', name, flags=re.IGNORECASE) != None:
                inner_zipfiles.append(name)
    logger.debug('Found {} zipped files'.format(len(inner_zipfiles)))
    return inner_zipfiles


def extract_files(zipfilename, pattern, output_dir):
    """Extracts all files that match a specific `pattern` from
    a zipped file.
    This stores files in memory!
    """

    # Compile the pattern if needed
    if not hasattr(pattern, 'search'):
        pattern = re.compile(pattern)

    logger.debug('Reading {}'.format(zipfilename))

    with zipfile.ZipFile(zipfilename, 'r') as zfile:
        for name in zfile.namelist():

            filename = os.path.basename(name)

            # skip directories
            if not filename:
                continue

            # filter files using the given pattern
            if pattern.search(name) is None:
                continue

            # copy file (taken from zipfile's extract)
            source = zfile.open(name)
            target = open(os.path.join(output_dir, filename), 'wb')
            with source, target:
                logger.debug("Extracting {s} to {t}".format(
                             s=source.name, t=target.name))
                shutil.copyfileobj(source, target)


def decompress_gzipped_file(filepath):
    assert filepath.endswith('.gz')
    logger.debug("Decompressing {}".format(filepath))
    source = gzip.open(filepath, 'rb')
    target = open(filepath[:-3], 'wb')
    with source, target:
        target.write(source.read())
        time.sleep(.5)
    logger.debug("Removing {}".format(filepath))
    os.remove(filepath)


def decompress_gzipped_files(directory):
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        decompress_gzipped_file(filepath)


def move_files_inside_folders(directory):
    pattern = re.compile(r'_(\d+)_')
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        new_dir_name = pattern.search(filename).group(1)
        # new_dir_name = os.path.splitext(filename)[0]
        new_dir_path = os.path.join(directory, new_dir_name)
        os.mkdir(new_dir_path)

        new_filepath = os.path.join(new_dir_path, filename)
        logger.debug("Moving {} to {}".format(filepath, new_filepath))
        shutil.move(filepath, new_filepath)
        time.sleep(.5)


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    if os.path.exists('test'):
        shutil.rmtree('test')

    # retrieve_inner_zipfiles('test.zip')
    # extract_files('test.zip', r'001', 't2')
    extract_nested_zips('test.zip', r'_warped\.')

    decompress_gzipped_files('test')

    move_files_inside_folders('test')
