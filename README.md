# imagespec-fast-builder

[![PyPI - Version](https://img.shields.io/pypi/v/imagespec-fast-builder.svg)](https://pypi.org/project/imagespec-fast-builder)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/imagespec-fast-builder.svg)](https://pypi.org/project/imagespec-fast-builder)

-----

`imagespec-fast-builder` is alternative backend for `flytekit`'s `ImageSpec` with the following improvements:

- Smaller images by using multi-stage builds, a smaller base image, and `conda-pack`
- Uses `uv` for installing from `PyPI`
- No additional Python dependencies

## Installation

```console
pip install imagespec-fast-builder
```

## How to use

After installing, set `ImageSpec`'s builder to `fast-builder`:

```python
from flytekit import ImageSpec

image = ImageSpec(
    builder="fast-builder",
    packages=["numpy"],
    registry="localhost:30000",  # Any registry
)
```

## License

`imagespec-fast-builder` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
