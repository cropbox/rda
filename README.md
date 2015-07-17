## Dependencies
The project requires Python 3.4. It used to be developed on Python 2.7, so most parts are still expected to work, but no longer guaranteed.

Here is a list of required modules:

- [numpy](https://github.com/numpy/numpy) : for any math
- [scipy](https://github.com/scipy/scipy): optimization
- [matplotlib](https://github.com/matplotlib/matplotlib): graphs
  - [seaborn](https://github.com/mwaskom/seaborn): more pretty graphs
- [pandas](https://github.com/pydata/pandas): structured data
  - [tables](https://github.com/PyTables/PyTables): read/writes HDF5 files
  - [xlrd](https://github.com/python-excel/xlrd): reads Excel files
- [ipython](https://github.com/ipython/ipython): better console
  - [tornado](https://github.com/tornadoweb/tornado): run [IPython Notebook](http://ipython.org/notebook.html)
  - [jsonschema](https://github.com/Julian/jsonschema)

Use `pip` to install them. Creating its own virtual environment with [virtualenvwrapper](https://bitbucket.org/dhellmann/virtualenvwrapper/) would be a good idea. If you use [Anaconda](https://store.continuum.io/cshop/anaconda/), they are probably already available on your system.


## Directory

- `code`: `main` module to run `pheno` package
  - `pheno`
    - `estimation`
    - `model`
    - `util`
- `input`: meteorological/observation datasets (.h5)
  - `raw`: original datasets from each source
    - `met`
    - `obs`
  - `df`: converted datasets in pandas `DataFrame`
    - `met`
    - `obs`
- `output`: generated results (.csv, .png)
  - `...`
  - `current`
    - `coeffs`: calibrated parameter sets
    - `suite`: from `ModelSuite` (a suite of models run on a single location/cultivar)
    - `group`: from `ModelGroup` (a group of suites run on a dataset, likely consists of multiple locations/cultivars)
    - `collection`: from `ModelCollection` (a collection of groups run on multiple datasets, mostly for aggregating cross-validation results)

Note that the datasets for `input` directory are **not** included in this repository due to file size limit. They can be found at the SPACE drive:

- Windows: `\\main.sefs.uw.edu\main\Space\Kim\Projects\RDA\work\input`
- Mac/Linux: `smb://main.sefs.uw.edu/main/Space/Kim/Projects/RDA/work/input`

Copy the contents of `input` into your local repository. Make sure you have the exactly same directory structure as above. In the future, they may be moved into [Git Large File Storage](https://git-lfs.github.com/) when it becomes available.


## Get Started
Run `IPython` on `code` directory to access `pheno` package. You may also want to read [the tutorial](code/Tutorial.ipynb) written in IPython notebook.
