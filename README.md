Django hadoop storage provide python classes/functions
to use [hadoop file system](https://hadoop.apache.org/docs/r1.2.1/hdfs_design.html) 
 (hdfs) with django storage.


Based on [libhdfs](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/LibHdfs.html) 
official hadoop python connector and [pyarrow](https://arrow.apache.org/docs/python/filesystems.html)
library.


### Requirements
- Install java-1.8.0-openjdk-devel, In centos 7
```bash
sudo yum install -y java-1.8.0-openjdk-devel
```

In Ubuntu
```bash
sudo apt-get install openjdk-8-jdk
```


- [Install hadoop](https://www.vultr.com/docs/how-to-install-hadoop-in-stand-alone-mode-on-centos-7)



### Settings
For use hdfs as django storage set:

```python
HADOOP_HOST = 'localhost'  # set your own host
HADOOP_PORT = 8020  # set your own port
HADOOP_USER = 'hadoop'  # set your own user
HADOOP_HOME = '/usr/lib/hadoop/'  # set your own path

MEDIA_ROOT = '/media/'
DEFAULT_FILE_STORAGE = 'hadoop_storage.HadoopStorage'
```

### Storage
Use hadoop file storage with same methods and properties that 
[django File Storage](https://docs.djangoproject.com/en/3.0/ref/files/storage/)

