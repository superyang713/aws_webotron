from setuptools import setup


setup(
    name='webotron-80',
    version='0.1',
    author='Yang Dai',
    author_email='daiy@mit.edu',
    description='Webotron 80 is a tool to deploy static website to aws.',
    license='GPLv3+',
    packages=['webotron'],
    url='https://github.com/superyang713/aws_webotron',
    install_requires=[
        'click',
        'boto3',
    ],
    entry_points="""
        [console_scripts]
        webotron=webotron.webotron:cli
    """
)
