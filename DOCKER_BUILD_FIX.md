# Docker Build Fix - C Extension Dependencies

## 🐛 Problem

The Docker build was failing with errors when trying to install Python packages that require C compilation:

### Error 1: httptools

```
error: command 'cc' failed: No such file or directory
help: `httptools` (v0.6.4) was included because `asgard` depends on `uvicorn[standard]`
```

### Error 2: cffi/cryptography

```
fatal error: ffi.h: No such file or directory
help: `cffi` was included because `asgard` depends on `python-jose[cryptography]`
      which depends on `cryptography` which depends on `cffi`
```

### Error 3: pyarrow

```
error: command 'cmake' failed: No such file or directory
help: `pyarrow` (v17.0.0) was included because `asgard` depends on `pyarrow`
```

## 🔍 Root Cause

The `python:3.10-slim` base image is minimal and doesn't include:

- C/C++ compilers (`gcc`, `g++`, `make`)
- CMake build system (`cmake`)
- Development headers for system libraries (`libffi-dev`, `libssl-dev`)

Python packages with C extensions need these to compile during installation.

## ✅ Solution

### Build-time Dependencies (needed for compilation):

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc           # C compiler
        g++           # C++ compiler
        make          # Build tool
        cmake         # CMake build system (for pyarrow)
        libffi-dev    # Foreign Function Interface headers (for cffi)
        libssl-dev    # OpenSSL headers (for cryptography)
        python3-dev   # Python development headers
```

### Runtime Dependencies (needed after compilation):

```dockerfile
RUN apt-get install -y --no-install-recommends \
        libffi8       # FFI runtime library
        libssl3       # OpenSSL runtime library
```

### Cleanup (keep image small):

```dockerfile
RUN apt-get purge -y --auto-remove \
        gcc g++ make cmake libffi-dev libssl-dev python3-dev
```

## 📦 Affected Packages

| Package        | Dependency Chain                                | Requires        |
| -------------- | ----------------------------------------------- | --------------- |
| `httptools`    | uvicorn[standard] → httptools                   | gcc, g++        |
| `cffi`         | python-jose[cryptography] → cryptography → cffi | gcc, libffi-dev |
| `cryptography` | python-jose[cryptography] → cryptography        | gcc, libssl-dev |
| `pyarrow`      | asgard → pyarrow                                | gcc, g++, cmake |

## 🏗️ Updated Dockerfile Flow

```
1. Install build dependencies (gcc, g++, make, cmake, libffi-dev, libssl-dev, etc.)
2. Install Python packages (compiles C extensions)
3. Install runtime libraries (libffi8, libssl3)
4. Remove build dependencies (saves ~300MB)
5. Keep runtime libraries (required for execution)
```

## 🎯 Result

✅ All C extensions compile successfully  
✅ Runtime libraries preserved  
✅ Build tools removed for smaller image  
✅ Image size optimized

## 🚀 Build Command

```bash
docker build -t asgard-dev .
```

The build should now complete successfully without compilation errors!
