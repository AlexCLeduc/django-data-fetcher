import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="django-data-fetcher",
    version="1.1.0",
    author="AlexCLeduc",
    # author_email="author@example.com",
    # description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AlexCleduc/data-fetcher",
    packages=[
        # find_packages() also includes extraneous stuff, like testing and sample_app
        package
        for package in setuptools.find_packages()
        if package.startswith("data_fetcher")
    ],
    install_requires=["django-middleware-global-request>=0.3"],
    tests_require=["django"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
