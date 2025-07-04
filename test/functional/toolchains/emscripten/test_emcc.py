# Test suite to check conan capabilities for cross compiling to web assembly and asmjs
import textwrap
import os
import platform
from shutil import rmtree
import pytest
import sys

from conan.test.utils.tools import TestClient

EMCC_MIN_PYTHON_VERSION = (3, 8)

base_emscripten_profile = textwrap.dedent(
    """
    [settings]
    build_type=Release
    compiler=emcc
    compiler.cppstd=17
    compiler.libcxx=libc++
    compiler.version=4.0.10
    os=Emscripten

    [conf]
    tools.build:exelinkflags=['-sALLOW_MEMORY_GROWTH=1']
    tools.build:sharedlinkflags=['-sALLOW_MEMORY_GROWTH=1']

    # Define the emcc executable paths
    tools.build:compiler_executables={'c':'emcc', 'cpp':'em++'}

    # Set Ninja as default generator as it is faster and will sove issues on Windows
    tools.cmake.cmaketoolchain:generator=Ninja
    # Verbosity to see emcc invocations
    tools.compilation:verbosity=verbose
    # Distinguish between architectures
    tools.cmake.cmake_layout:build_folder_vars=['settings.build_type', 'settings.arch']

    [buildenv]
    AR=emar
    NM=emnm
    RANLIB=emranlib
    STRIP=emstrip
"""
)

wasm32_profile = textwrap.dedent(
    """
    include(base_emscripten_profile)
    [settings]
    arch=wasm

    [conf]
    tools.build:exelinkflags+=['-sMAXIMUM_MEMORY=4GB', '-sINITIAL_MEMORY=64MB']
    tools.build:sharedlinkflags+=['-sMAXIMUM_MEMORY=4GB', '-sINITIAL_MEMORY=64MB']
    """
)

wasm_64_profile = textwrap.dedent(
    """
    include(base_emscripten_profile)
    [settings]
    arch=wasm64
    [conf]
    tools.build:exelinkflags+=['-sMAXIMUM_MEMORY=16GB', '-sINITIAL_MEMORY=16GB']
    tools.build:sharedlinkflags+=['-sMAXIMUM_MEMORY=16GB', '-sINITIAL_MEMORY=16GB']
    """
)


asmjs_profile = textwrap.dedent(
    """
    include(base_emscripten_profile)
    [settings]
    arch=asm.js

    [conf]
    tools.build:exelinkflags+=['-sMAXIMUM_MEMORY=2GB', '-sINITIAL_MEMORY=64MB']
    tools.build:sharedlinkflags+=['-sMAXIMUM_MEMORY=2GB', '-sINITIAL_MEMORY=64MB']
    """
)


@pytest.mark.tool("cmake")
@pytest.mark.tool("emcc")
@pytest.mark.tool("node")
@pytest.mark.skipif(sys.version_info < EMCC_MIN_PYTHON_VERSION, reason = "emcc requires Python 3.8 or higher")
@pytest.mark.skipif(platform.system() == "Windows", reason = "Emscripten not installed in Windows")
def test_cmake_emscripten():
    client = TestClient()

    client.run("new cmake_exe -d name=hello -d version=0.1")
    client.save({"wasm32": wasm32_profile, "asmjs": asmjs_profile, "base_emscripten_profile": base_emscripten_profile,})

    client.run("build . -pr:h=wasm32")
    assert "Conan toolchain: Defining libcxx as C++ flags: -stdlib=libc++" in client.out
    assert os.path.exists(os.path.join(client.current_folder, "build/release-wasm" , "hello.wasm"))

    # Run JavaScript generated code which uses .wasm file
    client.run_command("node ./build/release-wasm/hello")
    assert "Hello World Release!" in client.out

    client.run("build . -pr:h=asmjs")
    assert "WASM=0" in client.out
    # No wasm should have been generated for asm.js architecture
    assert not os.path.exists(os.path.join(client.current_folder, "build/release-asm.js" , "hello.wasm"))
    client.run_command("node ./build/release-asm.js/hello")
    assert "Hello World Release!" in client.out


@pytest.mark.tool("meson")
@pytest.mark.tool("emcc")
@pytest.mark.tool("node")
@pytest.mark.skipif(sys.version_info < EMCC_MIN_PYTHON_VERSION, reason = "emcc requires Python 3.8 or higher")
@pytest.mark.skipif(platform.system() == "Windows", reason = "Emscripten not installed in Windows")
def test_meson_emscripten():
    client = TestClient()
    client.run("new meson_exe -d name=hello -d version=0.1")

    client.save({"wasm32": wasm32_profile, "wasm64": wasm_64_profile, "asmjs": asmjs_profile, "base_emscripten_profile": base_emscripten_profile,})
    client.run("build . -pr:h=wasm64")
    assert "C++ compiler for the host machine: em++" in client.out
    assert "C++ linker for the host machine: em++ ld.wasm" in client.out
    assert "Host machine cpu family: wasm64" in client.out
    assert os.path.exists(os.path.join(client.current_folder, "build", "hello.wasm"))
    # wasm64 only supported since node v23 so only run in MacOS where it is available
    if platform.system() == "Darwin":
        client.run_command("node ./build/hello")
        assert "Hello World Release!" in client.out

    rmtree(os.path.join(client.current_folder, "build"))
    client.run("build . -pr:h=asmjs")
    assert "C++ compiler for the host machine: em++" in client.out
    assert "C++ linker for the host machine: em++ ld.wasm" in client.out
    assert "Host machine cpu family: asm.js" in client.out
    assert "WASM=0" in client.out

    assert not os.path.exists(os.path.join(client.current_folder, "build", "hello.wasm"))
    client.run_command("node ./build/hello")
    assert "Hello World Release!" in client.out


@pytest.mark.tool("autotools")
@pytest.mark.tool("emcc")
@pytest.mark.tool("node")
@pytest.mark.skipif(sys.version_info < EMCC_MIN_PYTHON_VERSION, reason = "emcc requires Python 3.8 or higher")
@pytest.mark.skipif(platform.system() == "Windows", reason = "Emscripten not installed in Windows")
def test_autotools_emscripten():
    client = TestClient(path_with_spaces=False)
    client.run("new autotools_exe -d name=hello -d version=0.1")
    client.save({"wasm32": wasm32_profile, "asmjs": asmjs_profile, "base_emscripten_profile": base_emscripten_profile,})
    client.run("build . -pr:h=wasm32")
    assert "checking for wasm32-local-emscripten-ranlib... emranlib" in client.out
    assert "checking for wasm32-local-emscripten-gcc... emcc" in client.out
    assert "checking for wasm32-local-emscripten-ar... emar" in client.out
    assert "checking the archiver (emar) interface... ar" in client.out
    assert "checking for wasm32-local-emscripten-strip... emstrip" in client.out

    assert os.path.exists(os.path.join(client.current_folder, "build-release", "src", "hello.wasm"))
    # Run JavaScript generated code which uses .wasm file
    client.run_command("node ./build-release/src/hello")
    assert "Hello World Release!" in client.out

    rmtree(os.path.join(client.current_folder, "build-release"))
    client.run("build . -pr:h=asmjs")
    assert "WASM=0" in client.out
    # No wasm should have been generated for asm.js architecture
    assert not os.path.exists(os.path.join(client.current_folder, "build-release", "hello.wasm"))
    client.run_command("node ./build-release/src/hello")
    assert "Hello World Release!" in client.out


@pytest.mark.tool("premake")
@pytest.mark.tool("emcc")
@pytest.mark.tool("node")
@pytest.mark.skipif(sys.version_info < EMCC_MIN_PYTHON_VERSION, reason = "emcc requires Python 3.8 or higher")
@pytest.mark.skipif(platform.system() != "Linux", reason = "Premake only installed in linux")
def test_premake_emscripten():
    client = TestClient()
    client.run("new premake_exe -d name=hello -d version=0.1")
    client.save({"wasm32": wasm32_profile, "asmjs": asmjs_profile, "base_emscripten_profile": base_emscripten_profile,})
    client.run("build . -pr:h=wasm32")
    assert "gmake --arch=wasm32" in client.out
    assert os.path.exists(os.path.join(client.current_folder, "build-release", "bin", "hello.wasm"))
    # Run JavaScript generated code which uses .wasm file
    client.run_command("node ./build-release/bin/hello")
    assert "Hello World Release!" in client.out
    rmtree(os.path.join(client.current_folder, "build-release"))

    client.run("build . -pr:h=asmjs")
    assert "WASM=0" in client.out
    # No wasm should have been generated for asm.js architecture
    assert not os.path.exists(os.path.join(client.current_folder, "build-release", "bin", "hello.wasm"))
    client.run_command("node ./build-release/bin/hello")
    assert "Hello World Release!" in client.out

# TODO: test_bazel_emscripten(): need WIP new bazel toolchain
# TODO: test_msbuild_emscripten(): give support to msbuild
