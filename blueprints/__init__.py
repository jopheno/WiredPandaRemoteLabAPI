import os, glob

__all__ = []
ignore_dirs = ['__pycache__']

root_dir = os.path.dirname(__file__)
dirs = [file for file in os.listdir(root_dir) if file not in ignore_dirs and os.path.isdir(os.path.join(root_dir, file))]

modules = glob.glob(os.path.join(root_dir, "*"))
__all__ = [os.path.basename(f)[:-3] for f in modules if f.endswith(".py") and not f.endswith("__init__.py") and not f.endswith("bp.py")]

# now for each dir
for dir in dirs:
    new_dir = os.path.join(root_dir, dir)
    modules = glob.glob(os.path.join(new_dir, "*"))
    new_files = [os.path.basename(f)[:-3] for f in modules if f.endswith(".py") and not f.endswith("__init__.py") and not f.endswith("bp.py")]
    for file in new_files:
        __all__.append(dir + '.' + file)
