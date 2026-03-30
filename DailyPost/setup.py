from setuptools import setup, find_packages

setup(
    name='DailyPost',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'google-api-python-client',
        'python-frontmatter',
        'google-auth-oauthlib',
        'html2text',
        # Add any other dependencies your project needs here
    ],
    entry_points={
        'console_scripts': [
            'dailypost=DailyPost.publisher:main',
        ],
    },
    author='Your Name', # Replace with your name
    author_email='your.email@example.com', # Replace with your email
    description='A tool for publishing and managing posts on Blogger.',
    long_description=open('README.md').read() if 'README.md' else '',
    long_description_content_type='text/markdown',
)