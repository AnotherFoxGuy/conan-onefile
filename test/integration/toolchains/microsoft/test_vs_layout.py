import os
import textwrap

from conan.test.utils.tools import TestClient


def test_vs_layout_subproject():
    c = TestClient()
    conanfile = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.microsoft import vs_layout
        class Pkg(ConanFile):
            settings = "os", "compiler", "build_type", "arch"
            generators = "MSBuildToolchain"
            def layout(self):
                self.folders.root = ".."
                self.folders.subproject = "pkg"
                vs_layout(self)
        """)
    c.save({"pkg/conanfile.py": conanfile})
    c.run("install pkg")
    assert os.path.isfile(os.path.join(c.current_folder, "pkg", "conan", "conantoolchain.props"))


def test_vs_layout_error():
    c = TestClient()
    conanfile = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.microsoft import vs_layout
        class Pkg(ConanFile):
            settings = "os", "compiler", "arch"
            def layout(self):
                vs_layout(self)
        """)
    c.save({"conanfile.py": conanfile})
    c.run("install .", assert_error=True)
    assert "The 'vs_layout' requires the 'build_type' setting" in c.out
    conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.microsoft import vs_layout
            class Pkg(ConanFile):
                settings = "os", "compiler", "build_type"
                def layout(self):
                    vs_layout(self)
            """)
    c.save({"conanfile.py": conanfile})
    c.run("install .", assert_error=True)
    assert "The 'vs_layout' requires the 'arch' setting" in c.out
    conanfile = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.microsoft import vs_layout
        class Pkg(ConanFile):
            settings = "os", "compiler", "build_type", "arch"
            def layout(self):
                vs_layout(self)
        """)
    c.save({"conanfile.py": conanfile})
    c.run("install . -s arch=riscv64", assert_error=True)
    assert "The 'vs_layout' doesn't work with the arch 'riscv64'" in c.out
    assert "Accepted architectures: 'x86', 'x86_64', 'armv7', 'armv8'" in c.out
