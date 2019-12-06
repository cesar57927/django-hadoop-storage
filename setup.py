import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='django-hadoop-storage',
    version='0.1.2',
    packages=setuptools.find_packages(),
    url='https://sofisis.com',
    license='BSD',
    author='Cesar Augusto Cadavid Lopera',
    author_email='cesar57927@gmail.com',
    description='Module for use hadoop file system (hdfs) as django storage',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Topic :: System :: Filesystems",
        "Development Status :: 5 - Production/Stable",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.6',
    install_requires=[
        'django',
        'pyarrow',
        'Unidecode',
    ]
)
