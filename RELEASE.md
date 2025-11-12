# PyPI Release Guide

This guide covers how to release new versions of `iriusrisk-cli` to PyPI.

## Prerequisites

### 1. Install Build Tools

```bash
pip install --upgrade build twine
```

### 2. Create PyPI Accounts

1. Create account at https://pypi.org/ (production)
2. Create account at https://test.pypi.org/ (testing)
3. Enable 2FA on both accounts (required for uploads)
4. Create API tokens:
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

### 3. Configure Twine (Optional but Recommended)

Create `~/.pypirc` to store credentials:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...your-token-here...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...your-testpypi-token-here...
```

**Important**: Set proper permissions: `chmod 600 ~/.pypirc`

## Release Process

### Step 1: Prepare the Release

1. **Update Version Number**

   Update version in both files:
   - `setup.py` (line 11)
   - `src/iriusrisk_cli/__init__.py` (line 3)

2. **Update CHANGELOG.md**

   Document changes in the new version:
   ```markdown
   ## [0.2.0] - YYYY-MM-DD
   
   ### Added
   - New feature descriptions
   
   ### Changed
   - Changes to existing functionality
   
   ### Fixed
   - Bug fixes
   
   ### Removed
   - Deprecated features removed
   ```

3. **Commit Version Changes**

   ```bash
   git add setup.py src/iriusrisk_cli/__init__.py CHANGELOG.md
   git commit -m "Bump version to 0.2.0"
   ```

### Step 2: Build the Package

1. **Clean Previous Builds**

   ```bash
   rm -rf build/ dist/ src/*.egg-info
   ```

2. **Build Distribution Files**

   ```bash
   python -m build
   ```

   This creates:
   - `dist/iriusrisk_cli-X.Y.Z.tar.gz` (source distribution)
   - `dist/iriusrisk_cli-X.Y.Z-py3-none-any.whl` (wheel)

3. **Verify Package Integrity**

   ```bash
   twine check dist/*
   ```

   Should see: `PASSED` for all files.

### Step 3: Test on TestPyPI

1. **Upload to TestPyPI**

   ```bash
   twine upload --repository testpypi dist/*
   ```

   Or with explicit credentials:
   ```bash
   twine upload --repository testpypi --username __token__ --password YOUR_TESTPYPI_TOKEN dist/*
   ```

2. **Test Installation from TestPyPI**

   Create a test virtual environment:
   ```bash
   python -m venv test-env
   source test-env/bin/activate  # On Windows: test-env\Scripts\activate
   
   # Install from TestPyPI
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ iriusrisk-cli
   
   # Test the installation
   iriusrisk --version
   iriusrisk --help
   
   # Deactivate and remove test environment
   deactivate
   rm -rf test-env
   ```

   **Note**: `--extra-index-url` is needed because dependencies (click, requests, etc.) are only on production PyPI.

### Step 4: Release to Production PyPI

Once TestPyPI installation is verified:

1. **Upload to Production PyPI**

   ```bash
   twine upload dist/*
   ```

   Or with explicit credentials:
   ```bash
   twine upload --username __token__ --password YOUR_PYPI_TOKEN dist/*
   ```

2. **Verify on PyPI**

   Check the package page: https://pypi.org/project/iriusrisk-cli/

3. **Test Production Installation**

   ```bash
   python -m venv test-env
   source test-env/bin/activate
   
   pip install iriusrisk-cli
   iriusrisk --version
   iriusrisk test  # Test connection (requires IriusRisk credentials)
   
   deactivate
   rm -rf test-env
   ```

### Step 5: Tag and Push Release

1. **Create Git Tag**

   ```bash
   git tag -a v0.2.0 -m "Release version 0.2.0"
   git push origin v0.2.0
   git push origin main
   ```

2. **Create GitHub Release** (if using GitHub)

   - Go to: https://github.com/iriusrisk/iriusrisk_cli/releases/new
   - Select the tag you just created
   - Title: `v0.2.0`
   - Copy release notes from CHANGELOG.md
   - Attach the distribution files from `dist/`
   - Click "Publish release"

## Post-Release Tasks

1. **Update README** (if needed)
   - Add PyPI version badge
   - Update installation instructions
   - Update compatibility notes

2. **Announce Release**
   - Post on relevant channels
   - Update documentation sites
   - Notify users of breaking changes

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Incompatible API changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

Examples:
- Bug fix: `0.1.0` → `0.1.1`
- New feature: `0.1.1` → `0.2.0`
- Breaking change: `0.2.0` → `1.0.0`

## Troubleshooting

### Upload Fails with 403 Error

- Verify API token is correct
- Ensure 2FA is enabled on your PyPI account
- Check token has upload permissions

### Package Already Exists

PyPI doesn't allow re-uploading the same version. You must:
1. Increment version number
2. Rebuild package
3. Upload new version

### Import Errors After Installation

- Verify all dependencies are listed in `install_requires` in `setup.py`
- Check package structure with `python -m zipfile -l dist/*.whl`
- Test in clean virtual environment

### Missing Files in Package

- Check `MANIFEST.in` includes necessary files
- Verify `package_data` in `setup.py` is correct
- Review build warnings for excluded files

## Initial Release Checklist

For the first release (0.1.0):

- [x] Package name `iriusrisk-cli` is available on PyPI
- [x] `setup.py` has complete metadata (URLs, keywords, classifiers)
- [x] `CHANGELOG.md` exists with release notes
- [x] `MANIFEST.in` explicitly includes all necessary files
- [x] `LICENSE` file exists (MIT License)
- [x] `README.md` has installation instructions
- [x] Build and test locally successful
- [ ] Test upload to TestPyPI successful
- [ ] Test installation from TestPyPI successful
- [ ] Upload to production PyPI successful
- [ ] Test installation from production PyPI successful
- [ ] Git tag created and pushed
- [ ] GitHub release created (if applicable)

## Quick Reference

```bash
# Complete release workflow
rm -rf build/ dist/ src/*.egg-info
python -m build
twine check dist/*
twine upload --repository testpypi dist/*
# Test installation
twine upload dist/*
git tag -a v0.X.Y -m "Release version 0.X.Y"
git push origin v0.X.Y
git push origin main
```

## Package Information

- **PyPI Package Name**: `iriusrisk-cli`
- **Command Name**: `iriusrisk`
- **Installation**: `pip install iriusrisk-cli`
- **Usage**: `iriusrisk --help`
- **PyPI URL**: https://pypi.org/project/iriusrisk-cli/
- **Repository**: https://github.com/iriusrisk/iriusrisk_cli

## Support

For questions or issues with the release process:
- Check PyPI documentation: https://packaging.python.org/
- Review setuptools guide: https://setuptools.pypa.io/
- Open an issue: https://github.com/iriusrisk/iriusrisk_cli/issues

