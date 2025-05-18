from setuptools import setup, find_packages

setup(
    name="christian_cleanup",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        'flask-login',
        'flask-migrate',
        'flask-apscheduler',
        'bootstrap-flask',
        'flask-rq2',
        'redis',
        'python-dotenv',
        'requests',
        'spotipy',
        'lyricsgenius',
        'transformers',
        'torch',
        'nltk',
        'pytest',
    ],
    python_requires='>=3.8',
)
