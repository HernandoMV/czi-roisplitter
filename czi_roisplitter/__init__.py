from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("czi-roisplitter")
except PackageNotFoundError:
    # package is not installed
    pass
