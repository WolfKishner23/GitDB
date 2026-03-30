from setuptools import setup, find_packages

setup(
    name='gitdb-sqlite',
    version='0.1.0',
    py_modules=['gitdb', 'snapshot_engine', 'diff_engine', 'api'],
    install_requires=[
        'click',
        'rich',
        'python-dotenv',
        'sqlglot',
        'flask',
        'flask-marshmallow',
        'marshmallow-sqlalchemy',
        'flask-cors',
        'marshmallow'
    ],
    entry_points={
        'console_scripts': [
            'gitdb=gitdb:cli',
        ],
    },
)
