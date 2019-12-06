import os
from datetime import datetime
from urllib.parse import urljoin

import pyarrow.hdfs
from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage
from django.core.signals import setting_changed
from django.utils import timezone
from django.utils._os import safe_join
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri
from django.utils.functional import cached_property
from django.utils.timezone import now
from unidecode import unidecode


def clean_char(char, replace=''):
    """
    Remove ['.',',','@'] and accents to char
    :param char: char
    :return: clean char
    """
    bad_tokens = [",", ";", ".",
                  "!", "'", ".",
                  "-", '"', "@",
                  r"\n", r"\r", '?',
                  '_']
    for delete in bad_tokens:
        char = char.replace(delete, replace)
    return char


@deconstructible
class HadoopStorage(Storage):
    hadoop_host: str = getattr(settings, 'HADOOP_HOST', 'localhost')
    hadoop_port: int = getattr(settings, 'HADOOP_PORT', 8020)
    hadoop_user: str = getattr(settings, 'HADOOP_USER', 'hadoop')
    hadoop_home: str = getattr(settings, 'HADOOP_HOME', '/usr/lib/hadoop/')
    replications: int = 3

    def __init__(self, location=None, base_url=None, file_permissions_mode=None,
                 directory_permissions_mode=None):
        self._location = location
        self._base_url = base_url
        self._file_permissions_mode = file_permissions_mode
        self._directory_permissions_mode = directory_permissions_mode

        # e['ARROW_LIBHDFS_DIR'] = '/opt/hadoop/hadoop/lib/native/'
        os.environ['HADOOP_HOME'] = self.hadoop_home
        # e['JAVA_HOME'] = "/usr/lib/jvm/java-11-openjdk-amd64"
        os.environ['CLASSPATH'] = f'{self.hadoop_home}/bin/hdfs classpath --glob'

        self.hdfs = pyarrow.hdfs.connect(
            self.hadoop_host, self.hadoop_port, user=self.hadoop_user,
            extra_conf={'dfs.replication': str(self.replications)})
        setting_changed.connect(self._clear_cached_properties)

    def _clear_cached_properties(self, setting, **kwargs):
        """Reset setting based property values."""
        if setting == 'MEDIA_ROOT':
            self.__dict__.pop('base_location', None)
            self.__dict__.pop('location', None)
        elif setting == 'MEDIA_URL':
            self.__dict__.pop('base_url', None)
        elif setting == 'FILE_UPLOAD_PERMISSIONS':
            self.__dict__.pop('file_permissions_mode', None)
        elif setting == 'FILE_UPLOAD_DIRECTORY_PERMISSIONS':
            self.__dict__.pop('directory_permissions_mode', None)

    def _value_or_setting(self, value, setting):
        return setting if value is None else value

    @property
    def path_prefix(self):
        """
        Set a prefix for all directories, usefull for pull apart directories by user session
        """
        return ''

    @cached_property
    def base_location(self):
        return self._value_or_setting(self._location, settings.MEDIA_ROOT)

    @cached_property
    def location(self):
        return os.path.abspath(self.base_location)

    @cached_property
    def base_url(self):
        if self._base_url is not None and not self._base_url.endswith('/'):
            self._base_url += '/'
        return self._value_or_setting(self._base_url, settings.MEDIA_URL)

    @cached_property
    def file_permissions_mode(self):
        return self._value_or_setting(self._file_permissions_mode, settings.FILE_UPLOAD_PERMISSIONS)

    @cached_property
    def directory_permissions_mode(self):
        return self._value_or_setting(self._directory_permissions_mode, settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS)

    def _open(self, name, mode='rb'):
        return File(self.hdfs.open(self.path(name), mode))

    def _save(self, name, content):
        full_path = self.path(name)
        hdfs = self.hdfs
        # Create any intermediate directories that do not exist.
        directory = os.path.dirname(full_path)
        if not hdfs.exists(directory):
            hdfs.mkdir(directory)

        # There's a potential race condition between get_available_name and
        # saving the file; it's possible that two threads might return the
        # same name, at which point all sorts of fun happens. So we need to
        # try to create the file, but if it already exists we have to go back
        # to get_available_name() and try again.
        hdfs.upload(full_path, content)

        # Store filenames with forward slashes, even on Windows.
        return name.replace('\\', '/')

    def delete(self, name):
        assert name, "The name argument is not allowed to be empty."
        name = self.path(name)
        # If the file or directory exists, delete it from the filesystem.
        if self.hdfs.exists(name):
            self.hdfs.delete(name)

    def get_available_name(self, name, max_length=100):
        # set a timestamp because hadoop override for same names
        dir_name, file_name = os.path.split(name)

        file_root, file_ext = os.path.splitext(file_name)
        file_root = unidecode(clean_char(file_root, '_'))

        # Validate if the name with the additional datetime ('%d%m%Y_%H%M%S%f') and the id_user_isis
        #  has more than 100 characters

        if max_length and (len(name) + 26) >= max_length:
            # Truncate file_root
            aux = len(name) - len(file_root)
            truncation = 74 - aux
            file_root = file_root[:truncation]

        file_name = "%s_%s%s" % (now().strftime('%d%m%Y_%H%M%S%f'), file_root, file_ext)
        return os.path.join(self.path_prefix, dir_name, file_name)

    def exists(self, name):
        return self.hdfs.exists(self.path(name))

    def listdir(self, path):
        path = self.path(path)

        directories, files = [], []
        for entry in self.hdfs.ls(path):
            if self.hdfs.info(entry)['kind'] == 'directory':
                directories.append(entry)
            elif self.hdfs.info(entry)['kind'] == 'file':
                files.append(entry)
        return directories, files

    def path(self, name):
        return safe_join(self.location, name)

    def size(self, name):
        return self.hdfs.info(self.path(name))['size']

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip('/')
        return urljoin(self.base_url, url)

    def _datetime_from_timestamp(self, ts):
        """
        If timezone support is enabled, make an aware datetime object in UTC;
        otherwise make a naive one in the local timezone.
        """
        if settings.USE_TZ:
            # Safe to use .replace() because UTC doesn't have DST
            return datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
        else:
            return datetime.fromtimestamp(ts)

    def get_accessed_time(self, name):
        return self._datetime_from_timestamp(self.hdfs.info(self.path(name))['last_accessed'])

    def get_created_time(self, name):
        # not exists created time on hadoop
        return self._datetime_from_timestamp(self.hdfs.info(self.path(name))['last_modified'])

    def get_modified_time(self, name):
        return self._datetime_from_timestamp(self.hdfs.info(self.path(name))['last_modified'])