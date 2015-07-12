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


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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


def uncompress_gzipped_file(file_obj):
    # FIXME
    assert file_obj.name.endswith('.gz')
    source = gzip.open(file_obj.name, 'rb')
    target = open(source.name[:-3], 'wb')
    with source, target:
        target.write(source.read())
    os.remove(source.name)


if __name__ == '__main__':

    if os.path.exists('test'):
        shutil.rmtree('test')

    # retrieve_inner_zipfiles('test.zip')
    # extract_files('test.zip', r'001', 't2')
    extract_nested_zips('test.zip', r'_warped\.')
