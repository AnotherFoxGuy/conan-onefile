import platform
import textwrap
import os

import pytest

from conan.test.assets.genconanfile import GenConanfile
from conan.test.utils.tools import TestClient


@pytest.mark.skipif(platform.system() not in ["Windows"], reason="Requires Windows")
@pytest.mark.parametrize("scope", ["build", "run", None])
def test_vcvars_generator(scope):
    client = TestClient(path_with_spaces=False)

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.microsoft import VCVars

        class TestConan(ConanFile):
            settings = "os", "compiler", "arch", "build_type"

            def generate(self):
                VCVars(self).generate({})
    """.format('scope="{}"'.format(scope) if scope else ""))

    client.save({"conanfile.py": conanfile})
    client.run('install . -s os=Windows -s compiler="msvc" -s compiler.version=191 '
               '-s compiler.cppstd=14 -s compiler.runtime=static')

    assert os.path.exists(os.path.join(client.current_folder, "conanvcvars.bat"))

    bat_contents = client.load("conanbuild.bat")
    if scope in ("build", None):
        assert "conanvcvars.bat" in bat_contents


@pytest.mark.skipif(platform.system() not in ["Windows"], reason="Requires Windows")
def test_vcvars_generator_skip():
    """
    tools.microsoft.msbuild:installation_path=disabled avoids creation of conanvcvars.bat
    """
    client = TestClient()
    client.save({"conanfile.py": GenConanfile().with_generator("VCVars")
                                               .with_settings("os", "compiler",
                                                              "arch", "build_type"),
                 "profile": 'include(default)\n[conf]\ntools.microsoft.msbuild:installation_path='})

    client.run('install . -c tools.microsoft.msbuild:installation_path=""')
    assert not os.path.exists(os.path.join(client.current_folder, "conanvcvars.bat"))
    client.run('install . -pr=profile')
    assert not os.path.exists(os.path.join(client.current_folder, "conanvcvars.bat"))


@pytest.mark.skipif(platform.system() not in ["Linux"], reason="Requires Linux")
def test_vcvars_generator_skip_on_linux():
    """
    Skip creation of conanvcvars.bat on Linux build systems
    """
    client = TestClient()
    client.save({"conanfile.py": GenConanfile().with_generator("VCVars")
                                               .with_settings("os", "compiler",
                                                              "arch", "build_type")})

    client.run('install . -s os=Windows -s compiler=msvc -s compiler.version=193 '
               '-s compiler.runtime=dynamic')
    assert not os.path.exists(os.path.join(client.current_folder, "conanvcvars.bat"))


@pytest.mark.skipif(platform.system() not in ["Windows"], reason="Requires Windows")
def test_vcvars_generator_string():
    client = TestClient(path_with_spaces=False)

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class TestConan(ConanFile):
            generators = "VCVars"
            settings = "os", "compiler", "arch", "build_type"
    """)
    client.save({"conanfile.py": conanfile})
    client.run('install . -s os=Windows -s compiler="msvc" -s compiler.version=191 '
               '-s compiler.cppstd=14 -s compiler.runtime=static')

    assert os.path.exists(os.path.join(client.current_folder, "conanvcvars.bat"))


@pytest.mark.skipif(platform.system() != "Windows", reason="Requires Windows")
@pytest.mark.xfail(reason="we dont have vs2015 installed in gh actions")
def test_vcvars_2015_error():
    # https://github.com/conan-io/conan/issues/9888
    client = TestClient(path_with_spaces=False)

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class TestConan(ConanFile):
            generators = "VCVars"
            settings = "os", "compiler", "arch", "build_type"
    """)
    client.save({"conanfile.py": conanfile})
    client.run('install . -s os=Windows -s compiler="msvc" -s compiler.version=190 '
               '-s compiler.cppstd=14 -s compiler.runtime=static')

    vcvars = client.load("conanvcvars.bat")
    assert 'vcvarsall.bat"  amd64' in vcvars
    assert "-vcvars_ver" not in vcvars


@pytest.mark.skipif(platform.system() != "Windows", reason="Requires Windows")
def test_vcvars_platform_x86():
    # https://github.com/conan-io/conan/issues/11144
    client = TestClient(path_with_spaces=False)

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class TestConan(ConanFile):
            generators = "VCVars"
            settings = "os", "compiler", "arch", "build_type"
    """)
    client.save({"conanfile.py": conanfile})
    client.run('install . -s os=Windows -s compiler="msvc" -s compiler.version=193 '
               '-s compiler.cppstd=14 -s compiler.runtime=static -s:b arch=x86')

    vcvars = client.load("conanvcvars.bat")
    assert 'vcvarsall.bat"  x86_amd64' in vcvars


@pytest.mark.skipif(platform.system() != "Windows", reason="Requires Windows")
def test_vcvars_winsdk_version():
    client = TestClient(path_with_spaces=False)

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class TestConan(ConanFile):
            generators = "VCVars"
            settings = "os", "compiler", "arch", "build_type"
    """)
    client.save({"conanfile.py": conanfile})
    client.run('install . -s os=Windows -s compiler=msvc -s compiler.version=193 '
               '-s compiler.cppstd=14 -s compiler.runtime=static '
               '-c tools.microsoft:winsdk_version=10.0')

    vcvars = client.load("conanvcvars.bat")
    assert 'vcvarsall.bat"  amd64 10.0 -vcvars_ver=14.3' in vcvars


@pytest.mark.skipif(platform.system() != "Windows", reason="Requires Windows")
def test_vcvars_compiler_update():
    client = TestClient(path_with_spaces=False)

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class TestConan(ConanFile):
            generators = "VCVars"
            settings = "os", "compiler", "arch", "build_type"
    """)
    client.save({"conanfile.py": conanfile})
    client.run('install . -s os=Windows -s compiler=msvc -s compiler.version=193 '
               '-s compiler.cppstd=14 -s compiler.runtime=static '
               '-s compiler.update=3')

    vcvars = client.load("conanvcvars.bat")
    assert 'vcvarsall.bat"  amd64 -vcvars_ver=14.33' in vcvars

@pytest.mark.skipif(platform.system() != "Windows", reason="Requires Windows")
def test_vcvars_armv8_windows_store():
    client = TestClient(path_with_spaces=False)

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class TestConan(ConanFile):
            generators = "VCVars"
            settings = "os", "compiler", "arch", "build_type"
    """)
    client.save({"conanfile.py": conanfile})
    client.run('install . -s:b os=Windows -s compiler="msvc" -s compiler.version=194 '
               '-s compiler.cppstd=14 -s compiler.runtime=static -s:h arch=armv8 '
               '-s:h os=WindowsStore -s:h os.version=10.0')

    vcvars = client.load("conanvcvars.bat")
    assert 'vcvarsall.bat"  amd64_arm64' in vcvars
