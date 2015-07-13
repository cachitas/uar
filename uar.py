"""
UAR - Unzip Alignment Results
=============================
"""

import logging
import gzip
import io
import os
import re
import shutil
import zipfile
import threading


logger = logging.getLogger(__name__)


class UAR(threading.Thread):

    def __init__(self, zipfilename, pattern, options, tasks_queue):
        super().__init__()
        self.zipfilename = zipfilename
        self.pattern = pattern
        self.options = options
        self.tasks_queue = tasks_queue

    def run(self):

        self.tasks_queue.put(
            ('running', dict(state='disabled'))
        )

        # Inspect zip file and set progressbar maximum value
        logger.info("Inspecting '%s'", self.zipfilename)
        inner_zipfiles = retrieve_inner_zipfiles(self.zipfilename)
        self.tasks_queue.put(
            ('update_progressbar_maximum', dict(maximum=len(inner_zipfiles)))
        )

        # Extract the files
        output_dir = os.path.splitext(self.zipfilename)[0]
        with zipfile.ZipFile(self.zipfilename, 'r') as zfile:
            for i, name in enumerate(inner_zipfiles):
                logger.info("Extracting '%s'", name)
                zfiledata = io.BytesIO(zfile.read(name))
                extract_files(zfiledata, self.pattern, output_dir)
                self.tasks_queue.put(
                    ('update_progressbar_value', dict(value=i+1))
                )
        logger.info("All files extracted to '{}'".format(output_dir))

        if self.options['degzip'] == 1:
            decompress_gzipped_files(output_dir)
            logger.info("Decompressed gzipped files")

        if self.options['tofolder'] == 1:
            move_files_inside_folders(output_dir)
            logger.info("Extracted files placed in its own folder")

        self.tasks_queue.put(
            ('done', dict())
        )


def extract_nested_zips(zipfilename, pattern):
    """Extract nested zipped files.

    Extracts desired files from within zipped files inside the given
    zipped file.

    The files extracted are placed inside a folder named after the
    provided zipped file.
    """

    output_dir = os.path.splitext(zipfilename)[0]

    inner_zipfiles = retrieve_inner_zipfiles(zipfilename)

    with zipfile.ZipFile(zipfilename, 'r') as zfile:
        for i, name in enumerate(inner_zipfiles):
            zfiledata = io.BytesIO(zfile.read(name))

            extract_files(zfiledata, pattern, output_dir)


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

    try:
        os.mkdir(output_dir)
    except OSError:
        logger.debug("Output directory already exists '{}'".format(output_dir))
    else:
        logger.debug("Creating output directory '{}'".format(output_dir))

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
    logger.debug("Removing {}".format(filepath))
    os.remove(filepath)


def decompress_gzipped_files(directory):
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        decompress_gzipped_file(filepath)


def move_files_inside_folders(directory):
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        new_dir_name = os.path.splitext(filename)[0]
        new_dir_path = os.path.join(directory, new_dir_name)
        os.mkdir(new_dir_path)

        new_filepath = os.path.join(new_dir_path, filename)
        logger.debug("Moving {} to {}".format(filepath, new_filepath))
        shutil.move(filepath, new_filepath)


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    if os.path.exists('test'):
        shutil.rmtree('test')

    # retrieve_inner_zipfiles('test.zip')
    # extract_files('test.zip', r'001', 't2')
    extract_nested_zips('test.zip', r'_warped\.')

    decompress_gzipped_files('test')

    move_files_inside_folders('test')
