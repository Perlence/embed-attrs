from setuptools import setup

setup(
    name='embed-attrs',
    version='0.1',
    author='Sviatoslav Abakumov',
    author_email='dust.harvesting@gmail.com',
    description='Borrow attributes from other classes by embedding them',
    url='https://github.com/Perlence/embed-attrs',
    download_url='https://github.com/Perlence/embed-attrs/archive/master.zip',
    py_modules=['embed'],
    zip_safe=False,
    install_requires=[
        'attrs>=16.3',
    ],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
