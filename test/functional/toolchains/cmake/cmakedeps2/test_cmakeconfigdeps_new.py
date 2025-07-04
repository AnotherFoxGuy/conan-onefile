import os
import platform
import re
import textwrap

import pytest

from conan.test.assets.genconanfile import GenConanfile
from conan.test.assets.sources import gen_function_h, gen_function_cpp
from conan.test.utils.tools import TestClient


new_value = "will_break_next"


@pytest.mark.tool("cmake")
class TestExes:
    @pytest.mark.parametrize("editable", [False, True])
    def test_exe(self, editable):
        conanfile = textwrap.dedent(r"""
            import os, platform
            from conan import ConanFile
            from conan.tools.cmake import CMake, cmake_layout

            class Test(ConanFile):
                name = "mytool"
                version = "0.1"
                package_type = "application"
                settings = "os", "arch", "compiler", "build_type"
                generators = "CMakeToolchain"
                exports_sources = "*"

                def layout(self):
                    cmake_layout(self)
                    self.cpp.build.exe = "mytool"
                    name = "mytool.exe" if platform.system() == "Windows" else "mytool"
                    app_loc = os.path.join("build", str(self.settings.build_type), name)
                    self.cpp.build.location = app_loc

                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()

                def package(self):
                    cmake = CMake(self)
                    cmake.install()

                def package_info(self):
                    self.cpp_info.exe = "mytool"
                    self.cpp_info.set_property("cmake_target_name", "MyTool::myexe")
                    self.cpp_info.location = os.path.join("bin", "mytool")
            """)
        main = textwrap.dedent("""
            #include <iostream>
            #include <fstream>

            int main() {
                std::cout << "Mytool generating out.c!!!!!" << std::endl;
                std::ofstream f("out.c");
            }
            """)
        c = TestClient()
        c.run("new cmake_exe -d name=mytool -d version=0.1")
        c.save({"conanfile.py": conanfile,
                "src/main.cpp": main})
        if editable:
            c.run("editable add .")
        c.run("create .")

        for requires in ("tool_requires", "requires"):
            consumer = textwrap.dedent(f"""
                from conan import ConanFile
                from conan.tools.cmake import CMakeDeps, CMakeToolchain, CMake, cmake_layout
                class Consumer(ConanFile):
                    settings = "os", "compiler", "arch", "build_type"
                    {requires} = "mytool/0.1"

                    def generate(self):
                        deps = CMakeDeps(self)
                        deps.generate()
                        tc = CMakeToolchain(self)
                        tc.generate()

                    def layout(self):
                        cmake_layout(self)
                    def build(self):
                        cmake = CMake(self)
                        cmake.configure()
                        cmake.build()
                """)
            cmake = textwrap.dedent("""
                set(CMAKE_C_COMPILER_WORKS 1)
                set(CMAKE_C_ABI_COMPILED 1)
                cmake_minimum_required(VERSION 3.15)
                project(consumer C)

                find_package(mytool)
                add_custom_command(OUTPUT out.c COMMAND MyTool::myexe)
                add_library(myLib out.c)
                """)
            c.save({f"consumer_{requires}/conanfile.py": consumer,
                    f"consumer_{requires}/CMakeLists.txt": cmake})
            c.run(f"build consumer_{requires} -c tools.cmake.cmakedeps:new={new_value}")
            assert "find_package(mytool)" in c.out
            assert "target_link_libraries(..." not in c.out
            assert "Conan: Target declared imported executable 'MyTool::myexe'" in c.out
            assert "Mytool generating out.c!!!!!" in c.out

    def test_exe_components(self):
        conanfile = textwrap.dedent(r"""
            import os
            from conan import ConanFile
            from conan.tools.cmake import CMake

            class Test(ConanFile):
                name = "mytool"
                version = "0.1"
                package_type = "application"
                settings = "os", "arch", "compiler", "build_type"
                generators = "CMakeToolchain"
                exports_sources = "*"

                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()

                def package(self):
                    cmake = CMake(self)
                    cmake.install()

                def package_info(self):
                    self.cpp_info.components["my1exe"].exe = "mytool1"
                    self.cpp_info.components["my1exe"].set_property("cmake_target_name", "MyTool::my1exe")
                    self.cpp_info.components["my1exe"].location = os.path.join("bin", "mytool1")
                    self.cpp_info.components["my2exe"].exe = "mytool2"
                    self.cpp_info.components["my2exe"].set_property("cmake_target_name", "MyTool::my2exe")
                    self.cpp_info.components["my2exe"].location = os.path.join("bin", "mytool2")
            """)
        main = textwrap.dedent("""
            #include <iostream>
            #include <fstream>

            int main() {{
                std::cout << "Mytool{number} generating out{number}.c!!!!!" << std::endl;
                std::ofstream f("out{number}.c");
            }}
            """)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(proj CXX)

            add_executable(mytool1 src/main1.cpp)
            add_executable(mytool2 src/main2.cpp)

            install(TARGETS mytool1 DESTINATION "." RUNTIME DESTINATION bin)
            install(TARGETS mytool2 DESTINATION "." RUNTIME DESTINATION bin)
            """)
        c = TestClient()
        c.save({"conanfile.py": conanfile,
                "CMakeLists.txt": cmake,
                "src/main1.cpp": main.format(number=1),
                "src/main2.cpp": main.format(number=2)
                })
        c.run("create .")

        consumer = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.cmake import CMakeDeps, CMakeToolchain, CMake, cmake_layout
            class Consumer(ConanFile):
                settings = "os", "compiler", "arch", "build_type"
                tool_requires = "mytool/0.1"

                def generate(self):
                    deps = CMakeDeps(self)
                    deps.generate()
                    tc = CMakeToolchain(self)
                    tc.generate()
                def layout(self):
                    cmake_layout(self)
                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()
            """)
        cmake = textwrap.dedent("""
            set(CMAKE_C_COMPILER_WORKS 1)
            set(CMAKE_C_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(consumer C)

            find_package(mytool)
            add_custom_command(OUTPUT out1.c COMMAND MyTool::my1exe)
            add_custom_command(OUTPUT out2.c COMMAND MyTool::my2exe)
            add_library(myLib out1.c out2.c)
            """)
        c.save({"conanfile.py": consumer,
                "CMakeLists.txt": cmake}, clean_first=True)
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
        assert "Conan: Target declared imported executable 'MyTool::my1exe'" in c.out
        assert "Mytool1 generating out1.c!!!!!" in c.out
        assert "Conan: Target declared imported executable 'MyTool::my2exe'" in c.out
        assert "Mytool2 generating out2.c!!!!!" in c.out


@pytest.mark.tool("cmake")
class TestLibs:
    def test_libs(self, matrix_client):
        c = matrix_client
        c.run("new cmake_lib -d name=app -d version=0.1 -d requires=matrix/1.0")
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
        assert "find_package(matrix)" in c.out
        assert "target_link_libraries(... matrix::matrix)" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::matrix'" in c.out

    @pytest.mark.parametrize("shared", [False, True])
    def test_libs_transitive(self, transitive_libraries, shared):
        c = transitive_libraries
        c.run("new cmake_lib -d name=app -d version=0.1 -d requires=engine/1.0")
        shared = "-o engine/*:shared=True" if shared else ""
        c.run(f"build . {shared} -c tools.cmake.cmakedeps:new={new_value}")
        assert "find_package(engine)" in c.out
        assert "target_link_libraries(... engine::engine)" in c.out
        if shared:
            assert "matrix::matrix" not in c.out  # It is hidden as static behind the engine
            assert "Conan: Target declared imported SHARED library 'engine::engine'" in c.out
        else:
            assert "Conan: Target declared imported STATIC library 'matrix::matrix'" in c.out
            assert "Conan: Target declared imported STATIC library 'engine::engine'" in c.out

    # if not using cmake >= 3.23 the intermediate gamelib_test linkage fail
    @pytest.mark.tool("cmake", "3.27")
    @pytest.mark.parametrize("shared", [False, True])
    def test_multilevel(self, shared):
        # TODO: make this shared fixtures in conftest for multi-level shared testing
        c = TestClient(default_server_user=True)
        c.run("new cmake_lib -d name=matrix -d version=0.1")
        c.run(f"create . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value}")

        c.save({}, clean_first=True)
        c.run("new cmake_lib -d name=engine -d version=0.1 -d requires=matrix/0.1")
        c.run(f"create . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value}")

        c.save({}, clean_first=True)
        c.run("new cmake_lib -d name=gamelib -d version=0.1 -d requires=engine/0.1")

        # This specific CMake fails for shared libraries with old CMakeDeps in Linux
        cmake = textwrap.dedent("""\
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(gamelib CXX)

            find_package(engine CONFIG REQUIRED)

            add_library(gamelib src/gamelib.cpp)
            target_include_directories(gamelib PUBLIC include)
            target_link_libraries(gamelib PRIVATE engine::engine)

            add_executable(gamelib_test src/gamelib_test.cpp)
            target_link_libraries(gamelib_test PRIVATE gamelib)

            set_target_properties(gamelib PROPERTIES PUBLIC_HEADER "include/gamelib.h")
            install(TARGETS gamelib)
            """)
        # Testing that a local test executable links correctly with the new CMakeDeps
        # It fails with the old CMakeDeps
        c.save({"CMakeLists.txt": cmake,
               "src/gamelib_test.cpp": '#include "gamelib.h"\nint main() { gamelib(); }'})
        c.run(f"create . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value}")

        c.save({}, clean_first=True)
        c.run("new cmake_exe -d name=game -d version=0.1 -d requires=gamelib/0.1")
        c.run(f"create . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value}")

        assert "matrix/0.1: Hello World Release!"
        assert "engine/0.1: Hello World Release!"
        assert "gamelib/0.1: Hello World Release!"
        assert "game/0.1: Hello World Release!"

        # Make sure that transitive headers are private, fails to include, traits work
        game_cpp = c.load("src/game.cpp")
        for header in ("matrix", "engine"):
            new_game_cpp = f"#include <{header}.h>\n" + game_cpp
            c.save({"src/game.cpp": new_game_cpp})
            c.run(f"build . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value}",
                  assert_error=True)
            assert f"{header}.h" in c.out

        # Make sure it works downloading to another cache
        c.run("upload * -r=default -c")
        c.run("remove * -c")

        c2 = TestClient(servers=c.servers)
        c2.run("new cmake_exe -d name=game -d version=0.1 -d requires=gamelib/0.1")
        c2.run(f"create . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value}")

        assert "matrix/0.1: Hello World Release!"
        assert "engine/0.1: Hello World Release!"
        assert "gamelib/0.1: Hello World Release!"
        assert "game/0.1: Hello World Release!"


class TestLibsIntegration:
    def test_libs_no_location(self):
        # Integration test
        # https://github.com/conan-io/conan/issues/17256
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Dep(ConanFile):
                name = "dep"
                version = "0.1"
                settings = "build_type"
                def package_info(self):
                    self.cpp_info.libs = ["dep"]
            """)

        c.save({"dep/conanfile.py": dep,
                "app/conanfile.py": GenConanfile().with_requires("dep/0.1")
                                                  .with_settings("build_type")})

        c.run("create dep")
        c.run(f"install app -c tools.cmake.cmakedeps:new={new_value} -g CMakeDeps",
              assert_error=True)
        assert "ERROR: Error in generator 'CMakeDeps': dep/0.1: Cannot obtain 'location' " \
               "for library 'dep'" in c.out

    def test_custom_file_targetname(self):
        # Integration test
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Dep(ConanFile):
                name = "dep"
                version = "0.1"
                settings = "build_type"
                def package_info(self):
                    self.cpp_info.set_property("cmake_file_name", "MyDep")
                    self.cpp_info.set_property("cmake_target_name", "MyTargetDep")
                """)

        c.save({"dep/conanfile.py": dep,
                "pkg/conanfile.py": GenConanfile("pkg", "0.1").with_requires("dep/0.1"),
                "app/conanfile.py": GenConanfile().with_requires("pkg/0.1")
               .with_settings("build_type")})

        c.run("create dep")
        c.run("create pkg")
        c.run(f"install app -c tools.cmake.cmakedeps:new={new_value} -g CMakeDeps")
        targets_cmake = c.load("app/pkg-Targets-release.cmake")
        assert "find_dependency(MyDep REQUIRED CONFIG)" in targets_cmake
        assert 'set_property(TARGET pkg::pkg APPEND PROPERTY INTERFACE_LINK_LIBRARIES\n' \
               '             "$<$<CONFIG:RELEASE>:MyTargetDep>")' in targets_cmake


class TestLibsLinkageTraits:
    def test_linkage_shared_static(self):
        """
        the static library is skipped
        """
        c = TestClient()
        c.run("new cmake_lib -d name=matrix -d version=0.1")
        c.run(f"create . -c tools.cmake.cmakedeps:new={new_value} -tf=")

        c.save({}, clean_first=True)
        c.run("new cmake_lib -d name=engine -d version=0.1 -d requires=matrix/0.1")
        c.run(f"create . -o engine/*:shared=True -c tools.cmake.cmakedeps:new={new_value} -tf=")

        c.save({}, clean_first=True)
        c.run("new cmake_exe -d name=game -d version=0.1 -d requires=engine/0.1")
        c.run(f"create . -o engine/*:shared=True -c tools.cmake.cmakedeps:new={new_value} "
              "-c tools.compilation:verbosity=verbose")
        assert re.search(r"Skipped binaries(\s*)matrix/0.1", c.out)
        assert "matrix/0.1: Hello World Release!"
        assert "engine/0.1: Hello World Release!"
        assert "game/0.1: Hello World Release!"

    @pytest.mark.tool("cmake", "3.27")
    @pytest.mark.parametrize("shared", [False, True])
    def test_transitive_headers(self, shared):
        c = TestClient()
        c.run("new cmake_lib -d name=matrix -d version=0.1")
        c.run(f"create . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value} -tf=")

        c.save({}, clean_first=True)
        c.run("new cmake_lib -d name=engine -d version=0.1 -d requires=matrix/0.1")
        engine_h = c.load("include/engine.h")
        engine_h = "#include <matrix.h>\n" + engine_h
        c.save({"include/engine.h": engine_h})
        conanfile = c.load("conanfile.py")
        conanfile = conanfile.replace('self.requires("matrix/0.1")',
                                      'self.requires("matrix/0.1", transitive_headers=True)')
        c.save({"conanfile.py": conanfile})
        c.run(f"create . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value} -tf=")

        c.save({}, clean_first=True)
        c.run("new cmake_exe -d name=game -d version=0.1 -d requires=engine/0.1")
        c.run(f"build . -o *:shared={shared} -c tools.cmake.cmakedeps:new={new_value}")
        # it works


@pytest.mark.tool("cmake")
class TestLibsComponents:
    def test_libs_components(self, matrix_client_components):
        """
        explicit usage of components
        """
        c = matrix_client_components

        # TODO: Check that find_package(.. COMPONENTS nonexisting) fails
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)

            find_package(matrix CONFIG REQUIRED)
            add_executable(app src/app.cpp)
            # standard one, and a custom cmake_target_name one
            target_link_libraries(app PRIVATE matrix::module MatrixHeaders)
            """)
        app_cpp = textwrap.dedent("""
            #include "module.h"
            #include "headers.h"
            int main() { module(); headers();}
            """)
        c.save({"CMakeLists.txt": cmake,
                "src/app.cpp": app_cpp})
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
        assert "find_package(matrix)" in c.out
        assert "target_link_libraries(... matrix::matrix)" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::vector'" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::module'" in c.out
        if platform.system() == "Windows":
            c.run_command(r".\build\Release\app.exe")
            assert "Matrix headers __cplusplus: __cplusplus2014" in c.out

    def test_libs_components_default(self, matrix_client_components):
        """
        Test that the default components are used when no component is specified
        """
        c = matrix_client_components

        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")

        app_cpp = textwrap.dedent("""
            #include "module.h"
            int main() { module();}
            """)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)

            find_package(matrix CONFIG REQUIRED)
            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE matrix::matrix)
            """)
        c.save({"src/app.cpp": app_cpp,
                "CMakeLists.txt": cmake})
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
        assert "Conan: Target declared imported STATIC library 'matrix::vector'" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::module'" in c.out
        assert "Conan: Target declared imported INTERFACE library 'MatrixHeaders'" in c.out

    def test_libs_components_default_error(self, matrix_client_components):
        """
        Same as above, but it fails, because headers is not in the default components
        """
        c = matrix_client_components

        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")

        app_cpp = textwrap.dedent("""
            #include "module.h"
            #include "headers.h"
            int main() { module();}
            """)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)

            find_package(matrix CONFIG REQUIRED)
            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE matrix::matrix)
            """)
        c.save({"src/app.cpp": app_cpp,
                "CMakeLists.txt": cmake})
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}", assert_error=True)
        assert "Error in build() method, line 35" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::vector'" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::module'" in c.out
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)

            find_package(matrix CONFIG REQUIRED)
            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE matrix::matrix MatrixHeaders)
            """)
        c.save({"CMakeLists.txt": cmake})
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
        assert "Running CMake.build()" in c.out  # Now it doesn't fail

    def test_libs_components_transitive(self, matrix_client_components):
        """
        explicit usage of components
        matrix::module -> matrix::vector

        engine::bots -> engine::physix
        engine::physix -> matrix::vector
        engine::world -> engine::physix, matrix::module
        """
        c = matrix_client_components
        bots_h = gen_function_h(name="bots")
        bots_cpp = gen_function_cpp(name="bots", includes=["bots", "physix"], calls=["physix"])
        physix_h = gen_function_h(name="physix")
        physix_cpp = gen_function_cpp(name="physix", includes=["physix", "vector"], calls=["vector"])
        world_h = gen_function_h(name="world")
        world_cpp = gen_function_cpp(name="world", includes=["world", "physix", "module"],
                                     calls=["physix", "module"])

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.cmake import CMake
            from conan.tools.files import copy

            class Engine(ConanFile):
              name = "engine"
              version = "1.0"
              settings = "os", "compiler", "build_type", "arch"
              generators = "CMakeToolchain"
              exports_sources = "src/*", "CMakeLists.txt"

              requires = "matrix/1.0"
              generators = "CMakeDeps", "CMakeToolchain"

              def build(self):
                  cmake = CMake(self)
                  cmake.configure()
                  cmake.build()

              def package(self):
                  cmake = CMake(self)
                  cmake.install()

              def package_info(self):
                  self.cpp_info.set_property("cmake_file_name", "MyEngine")
                  self.cpp_info.components["bots"].libs = ["bots"]
                  self.cpp_info.components["bots"].includedirs = ["include"]
                  self.cpp_info.components["bots"].libdirs = ["lib"]
                  self.cpp_info.components["bots"].requires = ["physix"]

                  self.cpp_info.components["physix"].libs = ["physix"]
                  self.cpp_info.components["physix"].includedirs = ["include"]
                  self.cpp_info.components["physix"].libdirs = ["lib"]
                  self.cpp_info.components["physix"].requires = ["matrix::vector"]

                  self.cpp_info.components["world"].libs = ["world"]
                  self.cpp_info.components["world"].includedirs = ["include"]
                  self.cpp_info.components["world"].libdirs = ["lib"]
                  self.cpp_info.components["world"].requires = ["physix", "matrix::module"]
                  """)

        cmakelists = textwrap.dedent("""
               set(CMAKE_CXX_COMPILER_WORKS 1)
               set(CMAKE_CXX_ABI_COMPILED 1)
               cmake_minimum_required(VERSION 3.15)
               project(matrix CXX)

               find_package(matrix CONFIG REQUIRED)

               add_library(physix src/physix.cpp)
               add_library(bots src/bots.cpp)
               add_library(world src/world.cpp)

               target_link_libraries(physix PRIVATE matrix::vector)
               target_link_libraries(bots PRIVATE physix)
               target_link_libraries(world PRIVATE physix matrix::module)

               set_target_properties(bots PROPERTIES PUBLIC_HEADER "src/bots.h")
               set_target_properties(physix PROPERTIES PUBLIC_HEADER "src/physix.h")
               set_target_properties(world PROPERTIES PUBLIC_HEADER "src/world.h")
               install(TARGETS physix bots world)
               """)
        c.save({"src/physix.h": physix_h,
                "src/physix.cpp": physix_cpp,
                "src/bots.h": bots_h,
                "src/bots.cpp": bots_cpp,
                "src/world.h": world_h,
                "src/world.cpp": world_cpp,
                "CMakeLists.txt": cmakelists,
                "conanfile.py": conanfile})
        c.run("create .")

        c.save({}, clean_first=True)
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=engine/1.0")
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)

            find_package(MyEngine CONFIG REQUIRED)

            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE engine::bots)

            install(TARGETS app)
            """)
        app_cpp = textwrap.dedent("""
            #include "bots.h"
            int main() { bots();}
            """)
        c.save({"CMakeLists.txt": cmake,
                "src/app.cpp": app_cpp})
        c.run(f"create . -c tools.cmake.cmakedeps:new={new_value}")
        assert "find_package(MyEngine)" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::vector'" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::module'" in c.out
        assert "Conan: Target declared imported INTERFACE library 'matrix::matrix'" in c.out
        assert "Conan: Target declared imported STATIC library 'engine::bots'" in c.out
        assert "Conan: Target declared imported STATIC library 'engine::physix'" in c.out
        assert "Conan: Target declared imported STATIC library 'engine::world'" in c.out
        assert "Conan: Target declared imported INTERFACE library 'engine::engine'" in c.out

        assert "bots: Release!" in c.out
        assert "physix: Release!" in c.out
        assert "vector: Release!" in c.out

    def test_libs_components_multilib(self):
        """
        cpp_info.libs = ["lib1", "lib2"]
        """
        c = TestClient()
        vector_h = gen_function_h(name="vector")
        vector_cpp = gen_function_cpp(name="vector", includes=["vector"])
        module_h = gen_function_h(name="module")
        module_cpp = gen_function_cpp(name="module", includes=["module"])

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.cmake import CMake

            class Matrix(ConanFile):
                name = "matrix"
                version = "1.0"
                settings = "os", "compiler", "build_type", "arch"
                generators = "CMakeToolchain"
                exports_sources = "src/*", "CMakeLists.txt"

                generators = "CMakeDeps", "CMakeToolchain"

                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()

                def package(self):
                    cmake = CMake(self)
                    cmake.install()

                def package_info(self):
                    self.cpp_info.set_property("cmake_target_name", "MyMatrix::MyMatrix")
                    self.cpp_info.libs = ["module", "vector"]
                  """)

        cmakelists = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(matrix CXX)

            add_library(module src/module.cpp)
            add_library(vector src/vector.cpp)

            set_target_properties(vector PROPERTIES PUBLIC_HEADER "src/vector.h")
            set_target_properties(module PROPERTIES PUBLIC_HEADER "src/module.h")
            install(TARGETS module vector)
            """)
        c.save({"src/module.h": module_h,
                "src/module.cpp": module_cpp,
                "src/vector.h": vector_h,
                "src/vector.cpp": vector_cpp,
                "CMakeLists.txt": cmakelists,
                "conanfile.py": conanfile})
        c.run("create .")

        c.save({}, clean_first=True)
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)

            find_package(matrix CONFIG REQUIRED)

            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE MyMatrix::MyMatrix)

            install(TARGETS app)
            """)
        app_cpp = textwrap.dedent("""
            #include "vector.h"
            #include "module.h"
            int main() { vector();module();}
            """)
        c.save({"CMakeLists.txt": cmake,
                "src/app.cpp": app_cpp})
        c.run(f"create . -c tools.cmake.cmakedeps:new={new_value}")
        assert "Conan: Target declared imported STATIC library 'matrix::_vector'" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::_module'" in c.out
        assert "Conan: Target declared imported INTERFACE library 'MyMatrix::MyMatrix'" in c.out
        assert "matrix::matrix" not in c.out

        assert "vector: Release!" in c.out
        assert "module: Release!" in c.out
        assert "vector: Release!" in c.out

    def test_libs_components_multilib_component(self):
        """
        cpp_info.components["mycomp"].libs = ["lib1", "lib2"]
        """
        c = TestClient()

        vector_h = gen_function_h(name="vector")
        vector_cpp = gen_function_cpp(name="vector", includes=["vector"])
        module_h = gen_function_h(name="module")
        module_cpp = gen_function_cpp(name="module", includes=["module"])

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.cmake import CMake

            class Matrix(ConanFile):
                name = "matrix"
                version = "1.0"
                settings = "os", "compiler", "build_type", "arch"
                generators = "CMakeToolchain"
                exports_sources = "src/*", "CMakeLists.txt"

                generators = "CMakeDeps", "CMakeToolchain"

                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()

                def package(self):
                    cmake = CMake(self)
                    cmake.install()

                def package_info(self):
                    self.cpp_info.set_property("cmake_target_name", "MyMatrix::MyMatrix")
                    self.cpp_info.components["mycomp"].set_property("cmake_target_name",
                                                                    "MyComp::MyComp")
                    self.cpp_info.components["mycomp"].libs = ["module", "vector"]
                  """)

        cmakelists = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(matrix CXX)

            add_library(module src/module.cpp)
            add_library(vector src/vector.cpp)

            set_target_properties(vector PROPERTIES PUBLIC_HEADER "src/vector.h")
            set_target_properties(module PROPERTIES PUBLIC_HEADER "src/module.h")
            install(TARGETS module vector)
            """)
        c.save({"src/module.h": module_h,
                "src/module.cpp": module_cpp,
                "src/vector.h": vector_h,
                "src/vector.cpp": vector_cpp,
                "CMakeLists.txt": cmakelists,
                "conanfile.py": conanfile})
        c.run("create .")

        c.save({}, clean_first=True)
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)

            find_package(matrix CONFIG REQUIRED)

            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE MyMatrix::MyMatrix)

            install(TARGETS app)
            """)
        app_cpp = textwrap.dedent("""
            #include "vector.h"
            #include "module.h"
            int main() { vector();module();}
            """)
        c.save({"CMakeLists.txt": cmake,
                "src/app.cpp": app_cpp})
        c.run(f"create . -c tools.cmake.cmakedeps:new={new_value}")
        assert "Conan: Target declared imported STATIC library 'matrix::_mycomp_vector'" in c.out
        assert "Conan: Target declared imported STATIC library 'matrix::_mycomp_module'" in c.out
        assert "Conan: Target declared imported INTERFACE library 'MyMatrix::MyMatrix'" in c.out
        assert "matrix::matrix" not in c.out

        assert "vector: Release!" in c.out
        assert "module: Release!" in c.out
        assert "vector: Release!" in c.out


@pytest.mark.tool("cmake")
class TestHeaders:
    def test_header_lib(self, matrix_client):
        c = matrix_client
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import copy
            class EngineHeader(ConanFile):
                name = "engine"
                version = "1.0"
                requires = "matrix/1.0"
                exports_sources = "*.h"
                settings = "compiler"
                def package(self):
                    copy(self, "*.h", src=self.source_folder, dst=self.package_folder)
                def package_id(self):
                    self.info.clear()
                def package_info(self):
                    self.cpp_info.defines = ["MY_MATRIX_HEADERS_DEFINE=1",
                                             "MY_MATRIX_HEADERS_DEFINE2=1"]
                    # Few flags to cover that CMakeDeps doesn't crash with them
                    if self.settings.compiler == "msvc":
                        self.cpp_info.cxxflags = ["/Zc:__cplusplus"]
                        self.cpp_info.cflags = ["/Zc:__cplusplus"]
                        self.cpp_info.system_libs = ["ws2_32"]
                    else:
                        self.cpp_info.system_libs = ["m", "dl"]
                        # Just to verify CMake don't break
                    if self.settings.compiler == "gcc":
                        self.cpp_info.sharedlinkflags = ["-z lazy", "-s"]
                        self.cpp_info.exelinkflags = ["-z lazy", "-s"]
             """)
        engine_h = textwrap.dedent("""
            #pragma once
            #include <iostream>
            #include "matrix.h"
            #ifndef MY_MATRIX_HEADERS_DEFINE
            #error "Fatal error MY_MATRIX_HEADERS_DEFINE not defined"
            #endif
            #ifndef MY_MATRIX_HEADERS_DEFINE2
            #error "Fatal error MY_MATRIX_HEADERS_DEFINE2 not defined"
            #endif
            void engine(){ std::cout << "Engine!" <<std::endl; matrix(); }
            """)

        c.save({"conanfile.py": conanfile,
                "include/engine.h": engine_h})
        c.run("create .")

        app = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.cmake import CMake
            class EngineHeader(ConanFile):
                settings = "os", "compiler", "build_type", "arch"
                requires = "engine/1.0"
                generators = "CMakeDeps", "CMakeToolchain"
                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()
             """)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)
            find_package(engine CONFIG REQUIRED)
            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE engine::engine)
            """)
        c.save({"conanfile.py": app,
                "CMakeLists.txt": cmake,
                "src/app.cpp": gen_function_cpp(name="main", includes=["engine"], calls=["engine"])},
               clean_first=True)
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
        assert "Conan: Target declared imported STATIC library 'matrix::matrix'" in c.out
        assert "Conan: Target declared imported INTERFACE library 'engine::engine'" in c.out

    @pytest.mark.skipif(platform.system() != "Windows", reason="Only windows")
    def test_conditional_header(self):
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import copy
            class EngineHeader(ConanFile):
                name = "engine"
                exports_sources = "*.h"
                def package(self):
                    copy(self, "*.h", src=self.source_folder, dst=self.package_folder)
                def package_info(self):
                    self.cpp_info.defines = ["MY_MATRIX_HEADERS_{version}_DEFINE=1"]
            """)
        engine_h = textwrap.dedent("""
            #pragma once
            #include <iostream>

            #ifndef MY_MATRIX_HEADERS_{version}_DEFINE
            #error "Fatal error MY_MATRIX_HEADERS_{version}_DEFINE not defined"
            #endif
            void engine(){{ std::cout << "Engine {version}!" <<std::endl; }}
            """)

        c = TestClient()
        c.save({"conanfile.py": conanfile.format(version="1_0"),
                "include/engine.h": engine_h.format(version="1_0")})
        c.run("create . --version=1_0")
        c.save({"conanfile.py": conanfile.format(version="1_1"),
                "include/engine.h": engine_h.format(version="1_1")})
        c.run("create . --version=1_1")

        app = textwrap.dedent("""
            import os
            from conan import ConanFile
            from conan.tools.cmake import CMake, cmake_layout
            class EngineHeader(ConanFile):
                settings = "os", "compiler", "build_type", "arch"
                generators = "CMakeDeps", "CMakeToolchain"
                def requirements(self):
                    v = "1_0" if self.settings.build_type == "Debug" else "1_1"
                    self.requires(f"engine/{v}")
                def layout(self):
                    cmake_layout(self)
                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()
                    self.run(os.path.join(self.cpp.build.bindir, "app"))
             """)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(app CXX)
            find_package(engine CONFIG REQUIRED)
            add_executable(app src/app.cpp)
            target_link_libraries(app PRIVATE engine::engine)
            """)
        c.save({"conanfile.py": app,
                "CMakeLists.txt": cmake,
                "src/app.cpp": gen_function_cpp(name="main", includes=["engine"], calls=["engine"])},
               clean_first=True)
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
        assert "engine/1_1" in c.out
        assert "engine/1_0" not in c.out
        assert "Conan: Target declared imported INTERFACE library 'engine::engine'" in c.out
        assert "Engine 1_1!" in c.out

        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value} -s build_type=Debug")
        assert "engine/1_1" not in c.out
        assert "engine/1_0" in c.out
        assert "Conan: Target declared imported INTERFACE library 'engine::engine'" in c.out
        assert "Engine 1_0!" in c.out


class TestToolRequires:
    def test_tool_requires(self):
        """ tool-requires should not define the try-compile or global variables
        for includedirs, libraries, definitions, otherwise the build-context would
        override the host context"""
        c = TestClient()
        c.save({"tool/conanfile.py": GenConanfile("tool", "0.1"),
                "pkg/conanfile.py": GenConanfile("pkg", "0.1").with_settings("build_type")
                                                              .with_tool_requires("tool/0.1")})
        c.run("create tool")
        c.run(f"install pkg -g CMakeDeps -c tools.cmake.cmakedeps:new={new_value}")
        assert "find_package(tool) # Optional. This is a tool-require, " \
               "can't link its targets" in c.out
        assert "target_link_libraries" not in c.out
        tool_config = c.load("pkg/tool-config.cmake")
        assert 'set(tool_INCLUDE_DIRS' not in tool_config
        assert 'set(tool_INCLUDE_DIR' not in tool_config
        assert 'set(tool_LIBRARIES' not in tool_config


@pytest.mark.tool("cmake")
@pytest.mark.parametrize("tool_requires", [True, False])
def test_build_modules_custom_script(tool_requires):
    """
    it works both as a tool_requires and as a regular requirement
    """
    client = TestClient()
    conanfile = textwrap.dedent("""
        import os
        from conan import ConanFile
        from conan.tools.files import copy

        class Conan(ConanFile):
            name = "myfunctions"
            version = "1.0"
            exports_sources = ["*.cmake"]

            def package(self):
                copy(self, "*.cmake", self.source_folder, self.package_folder)

            def package_info(self):
                self.cpp_info.set_property("cmake_build_modules", ["myfunction.cmake"])
        """)

    myfunction = textwrap.dedent("""
        function(myfunction)
            message("Hello myfunction!!!!")
        endfunction()
        """)
    client.save({"conanfile.py": conanfile, "myfunction.cmake": myfunction})
    client.run("create .")

    requires = "tool_requires" if tool_requires else "requires"
    consumer = textwrap.dedent(f"""
        from conan import ConanFile
        from conan.tools.cmake import CMake

        class Conan(ConanFile):
            settings = "os", "compiler", "build_type", "arch"
            generators = "CMakeToolchain", "CMakeDeps"
            {requires} = "myfunctions/1.0"

            def build(self):
                cmake = CMake(self)
                cmake.configure()
        """)
    cmakelists = textwrap.dedent("""
        cmake_minimum_required(VERSION 3.15)
        project(test NONE)
        find_package(myfunctions CONFIG REQUIRED)
        myfunction()
        """)
    client.save({"conanfile.py": consumer,
                 "CMakeLists.txt": cmakelists},
                clean_first=True)
    client.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
    assert "Hello myfunction!!!!" in client.out


@pytest.mark.tool("cmake")
class TestProtobuf:

    @pytest.fixture()
    def protobuf(self):
        conanfile = textwrap.dedent(r"""
            import os
            from conan import ConanFile
            from conan.tools.cmake import CMake

            class Protobuf(ConanFile):
                name = "protobuf"
                version = "0.1"
                settings = "os", "arch", "compiler", "build_type"
                options = {"shared": [True, False]}
                default_options = {"shared": False}

                generators = "CMakeToolchain"
                exports_sources = "*"

                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()

                def package(self):
                    cmake = CMake(self)
                    cmake.install()

                def package_info(self):
                    self.cpp_info.set_property("cmake_file_name", "MyProtobuf")
                    self.cpp_info.components["protobuf"].libs = ["protobuf"]
                    self.cpp_info.components["protoc"].exe = "protoc"
                    self.cpp_info.components["protoc"].set_property("cmake_target_name",
                                                                    "Protobuf::Protocompile")
                    self.cpp_info.components["protoc"].location = os.path.join("bin", "protoc")
            """)
        main = textwrap.dedent("""
            #include <iostream>
            #include <fstream>
            #include "protobuf.h"

            int main() {
                protobuf();
                #ifdef NDEBUG
                std::cout << "Protoc RELEASE generating out.c!!!!!" << std::endl;
                #else
                std::cout << "Protoc DEBUG generating out.c!!!!!" << std::endl;
                #endif
                std::ofstream f("out.c");
            }
            """)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(protobuf CXX)

            add_library(protobuf src/protobuf.cpp)
            add_executable(protoc src/main.cpp)
            target_link_libraries(protoc PRIVATE protobuf)
            set_target_properties(protobuf PROPERTIES PUBLIC_HEADER "src/protobuf.h")

            install(TARGETS protoc protobuf)
            """)
        c = TestClient()
        c.save({"conanfile.py": conanfile,
                "CMakeLists.txt": cmake,
                "src/protobuf.h": gen_function_h(name="protobuf"),
                "src/protobuf.cpp": gen_function_cpp(name="protobuf", includes=["protobuf"]),
                "src/main.cpp": main})
        c.run("export .")

        consumer = textwrap.dedent("""
            import os
            from conan import ConanFile
            from conan.tools.cmake import CMake, cmake_layout
            class Consumer(ConanFile):
                settings = "os", "compiler", "arch", "build_type"
                requires = "protobuf/0.1"
                generators = "CMakeToolchain", "CMakeDeps"

                def layout(self):
                    cmake_layout(self)
                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()
                    self.run(os.path.join(self.cpp.build.bindir, "myapp"))
            """)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(consumer CXX)

            find_package(MyProtobuf CONFIG REQUIRED)
            add_custom_command(OUTPUT out.c COMMAND Protobuf::Protocompile)
            add_executable(myapp myapp.cpp out.c)
            target_link_libraries(myapp PRIVATE protobuf::protobuf)
            get_target_property(imported_configs Protobuf::Protocompile IMPORTED_CONFIGURATIONS)
            message(STATUS "Protoc imported configurations: ${imported_configs}!!!")
            """)
        myapp = textwrap.dedent("""
            #include <iostream>
            #include "protobuf.h"

            int main() {
                protobuf();
                std::cout << "MyApp" << std::endl;
            }
            """)
        c.save({"conanfile.py": consumer,
                "CMakeLists.txt": cmake,
                "myapp.cpp": myapp}, clean_first=True)
        return c

    def test_requires(self, protobuf):
        c = protobuf
        c.run(f"build . --build=missing -c tools.cmake.cmakedeps:new={new_value}")
        assert "Conan: Target declared imported STATIC library 'protobuf::protobuf'" in c.out
        assert "Conan: Target declared imported executable 'Protobuf::Protocompile'" in c.out
        assert "Protoc RELEASE generating out.c!!!!!" in c.out
        assert 'Protoc imported configurations: RELEASE!!!' in c.out

    def test_both(self, protobuf):
        consumer = textwrap.dedent("""
            import os
            from conan import ConanFile
            from conan.tools.cmake import CMake, cmake_layout
            class Consumer(ConanFile):
                settings = "os", "compiler", "arch", "build_type"
                requires = "protobuf/0.1"
                tool_requires = "protobuf/0.1"
                generators = "CMakeToolchain", "CMakeDeps"

                def layout(self):
                    cmake_layout(self)
                def build(self):
                    cmake = CMake(self)
                    cmake.configure()
                    cmake.build()
            """)
        c = protobuf
        c.save({"conanfile.py": consumer})
        c.run("build . -s:h build_type=Debug --build=missing "
              f"-c tools.cmake.cmakedeps:new={new_value}")

        assert "Conan: Target declared imported STATIC library 'protobuf::protobuf'" in c.out
        assert "Conan: Target declared imported executable 'Protobuf::Protocompile'" in c.out
        assert "Protoc RELEASE generating out.c!!!!!" in c.out
        assert "protobuf: Release!" in c.out
        assert "protobuf: Debug!" not in c.out
        assert 'Protoc imported configurations: RELEASE!!!' in c.out

        cmd = "./build/Debug/myapp" if platform.system() != "Windows" else r"build\Debug\myapp"
        c.run_command(cmd)
        assert "protobuf: Debug!" in c.out
        assert "protobuf: Release!" not in c.out

        c.run("build . --build=missing "
              f"-c tools.cmake.cmakedeps:new={new_value}")

        assert "Conan: Target declared imported STATIC library 'protobuf::protobuf'" in c.out
        assert "Conan: Target declared imported executable 'Protobuf::Protocompile'" in c.out
        assert "Protoc RELEASE generating out.c!!!!!" in c.out
        assert "protobuf: Release!" in c.out
        assert "protobuf: Debug!" not in c.out
        assert 'Protoc imported configurations: RELEASE!!!' in c.out

        cmd = "./build/Release/myapp" if platform.system() != "Windows" else r"build\Release\myapp"
        c.run_command(cmd)
        assert "protobuf: Debug!" not in c.out
        assert "protobuf: Release!" in c.out


@pytest.mark.tool("cmake", "3.27")
class TestConfigs:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Only MSVC multi-conf")
    def test_multi_config(self, matrix_client):
        c = matrix_client
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")
        c.run(f"install . -c tools.cmake.cmakedeps:new={new_value}")
        c.run("install . -s build_type=Debug --build=missing "
              f"-c tools.cmake.cmakedeps:new={new_value}")

        c.run_command("cmake --preset conan-default")
        c.run_command("cmake --build --preset conan-release")
        c.run_command("cmake --build --preset conan-debug")

        c.run_command("build\\Release\\app")
        assert "matrix/1.0: Hello World Release!" in c.out
        assert "app/0.1: Hello World Release!" in c.out
        c.run_command("build\\Debug\\app")
        assert "matrix/1.0: Hello World Debug!" in c.out
        assert "app/0.1: Hello World Debug!" in c.out

    def test_cross_config(self, matrix_client):
        # Release dependencies, but compiling app in Debug
        c = matrix_client
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")
        c.run(f"install . -s &:build_type=Debug -c tools.cmake.cmakedeps:new={new_value}")

        # With modern CMake > 3.26 not necessary set(CMAKE_MAP_IMPORTED_CONFIG_DEBUG Release)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.27)
            project(app CXX)
            # set(CMAKE_MAP_IMPORTED_CONFIG_DEBUG Release)
            find_package(matrix CONFIG REQUIRED)

            add_executable(app src/app.cpp src/main.cpp)
            target_link_libraries(app PRIVATE matrix::matrix)
            """)
        c.save({"CMakeLists.txt": cmake})

        preset = "conan-default" if platform.system() == "Windows" else "conan-debug"
        c.run_command(f"cmake --preset {preset}")
        c.run_command("cmake --build --preset conan-debug")

        c.run_command(os.path.join("build", "Debug", "app"))
        assert "matrix/1.0: Hello World Release!" in c.out
        assert "app/0.1: Hello World Debug!" in c.out

    def test_cross_config_components(self, matrix_client_components):
        # Release dependencies, but compiling app in Debug
        c = matrix_client_components
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")
        app_cpp = textwrap.dedent("""
            #include "app.h"
            #include "module.h"
            void app(){
               module();
            }""")
        c.save({"src/app.cpp": app_cpp,
                "src/main.cpp": gen_function_cpp(name="main", includes=["app"], calls=["app"])})

        c.run(f"install . -s &:build_type=Debug -c tools.cmake.cmakedeps:new={new_value}")
        # With modern CMake > 3.26 not necessary set(CMAKE_MAP_IMPORTED_CONFIG_DEBUG Release)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.27)
            project(app CXX)
            # set(CMAKE_MAP_IMPORTED_CONFIG_DEBUG Release)
            find_package(matrix CONFIG REQUIRED)

            add_executable(app src/app.cpp src/main.cpp)
            target_link_libraries(app PRIVATE matrix::matrix)
            """)
        c.save({"CMakeLists.txt": cmake})

        preset = "conan-default" if platform.system() == "Windows" else "conan-debug"
        c.run_command(f"cmake --preset {preset}")
        c.run_command("cmake --build --preset conan-debug")

        c.run_command(os.path.join("build", "Debug", "app"))
        assert "main: Debug!" in c.out
        assert "module: Release!" in c.out
        assert "vector: Release!" in c.out

    @pytest.mark.skipif(platform.system() == "Windows", reason="This doesn't work in MSVC")
    def test_cross_config_implicit(self, matrix_client):
        # Release dependencies, but compiling app in Debug, without specifying it
        c = matrix_client
        c.run("new cmake_exe -d name=app -d version=0.1 -d requires=matrix/1.0")
        c.run(f"install . -c tools.cmake.cmakedeps:new={new_value}")

        # With modern CMake > 3.26 not necessary set(CMAKE_MAP_IMPORTED_CONFIG_DEBUG Release)
        cmake = textwrap.dedent("""
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.27)
            project(app CXX)
            # set(CMAKE_MAP_IMPORTED_CONFIG_DEBUG Release)
            find_package(matrix CONFIG REQUIRED)

            add_executable(app src/app.cpp src/main.cpp)
            target_link_libraries(app PRIVATE matrix::matrix)
            """)

        c.save({"CMakeLists.txt": cmake})
        # Now we can force the Debug build, even if dependencies are Release
        c.run_command("cmake . -DCMAKE_BUILD_TYPE=Debug -B build "
                      "-DCMAKE_PREFIX_PATH=build/Release/generators")
        c.run_command("cmake --build build")
        c.run_command("./build/app")
        assert "matrix/1.0: Hello World Release!" in c.out
        assert "app/0.1: Hello World Debug!" in c.out


@pytest.mark.tool("cmake", "3.23")
class TestCMakeTry:

    def test_check_c_source_compiles(self, matrix_client):
        """
        https://github.com/conan-io/conan/issues/12012
        """
        c = matrix_client  # it brings the "matrix" package dependency pre-built

        consumer = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.cmake import CMakeDeps
            class PkgConan(ConanFile):
                settings = "os", "arch", "compiler", "build_type"
                requires = "matrix/1.0"
                generators = "CMakeToolchain",
                def generate(self):
                    deps = CMakeDeps(self)
                    deps.set_property("matrix", "cmake_additional_variables_prefixes", ["MyMatrix"])
                    deps.generate()
            """)

        cmakelist = textwrap.dedent("""\
            set(CMAKE_CXX_COMPILER_WORKS 1)
            set(CMAKE_CXX_ABI_COMPILED 1)
            cmake_minimum_required(VERSION 3.15)
            project(Hello LANGUAGES CXX)

            find_package(matrix CONFIG REQUIRED)
            include(CheckCXXSourceCompiles)

            set(CMAKE_REQUIRED_INCLUDES ${MyMatrix_INCLUDE_DIRS})
            set(CMAKE_REQUIRED_LIBRARIES ${MyMatrix_LIBRARIES})
            check_cxx_source_compiles("#include <matrix.h>
                                      int main(void) { matrix();return 0; }" IT_COMPILES)
            """)

        c.save({"conanfile.py": consumer,
                "CMakeLists.txt": cmakelist}, clean_first=True)
        c.run(f"install . -c tools.cmake.cmakedeps:new={new_value}")

        preset = "conan-default" if platform.system() == "Windows" else "conan-release"
        c.run_command(f"cmake --preset {preset} ")
        assert "Performing Test IT_COMPILES - Success" in c.out


class TestCMakeComponents:

    @pytest.mark.tool("cmake")
    @pytest.mark.parametrize("components, found", [("comp1", True), ("compX", False)])
    def test_components(self, components, found):
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                name = "dep"
                version = "0.1"
                def package_info(self):
                    self.cpp_info.set_property("cmake_components", ["comp1", "comp2"])
            """)
        c.save({"conanfile.py": dep})
        c.run("create .")

        consumer = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.cmake import CMake
            class PkgConan(ConanFile):
                settings = "os", "arch", "compiler", "build_type"
                requires = "dep/0.1"
                generators = "CMakeToolchain", "CMakeDeps"
                def build(self):
                    deps = CMake(self)
                    deps.configure()
            """)

        cmakelist = textwrap.dedent(f"""\
            cmake_minimum_required(VERSION 3.15)
            project(Hello LANGUAGES NONE)

            find_package(dep CONFIG REQUIRED COMPONENTS {components})
            """)

        c.save({"conanfile.py": consumer,
                "CMakeLists.txt": cmakelist}, clean_first=True)
        c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}", assert_error=not found)
        if not found:
            assert f"Conan: Error: 'dep' required COMPONENT '{components}' not found" in c.out

    def test_components_default_definition(self):
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                name = "dep"
                version = "0.1"
                def package_info(self):
                    # private component that should be skipped
                    self.cpp_info.components["_private"].includedirs = ["include"]
                    self.cpp_info.components["c1"].set_property("cmake_target_name", "MyC1")
                    self.cpp_info.components["c2"].set_property("cmake_target_name", "Dep::MyC2")
                    self.cpp_info.components["c3"].includedirs = ["include"]
            """)
        c.save({"conanfile.py": dep})
        c.run("create .")
        c.run(f"install --requires=dep/0.1 -g CMakeDeps -c tools.cmake.cmakedeps:new={new_value}")
        cmake = c.load("dep-config.cmake")
        assert 'set(dep_PACKAGE_PROVIDED_COMPONENTS MyC1 MyC2 c3)' in cmake

    def test_components_individual_names(self):
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                name = "dep"
                version = "0.1"
                def package_info(self):
                    self.cpp_info.components["c1"].set_property("cmake_target_name", "MyC1")
                    self.cpp_info.components["c1"].set_property("cmake_components", ["MyCompC1"])
                    self.cpp_info.components["c2"].set_property("cmake_target_name", "Dep::MyC2")
                    self.cpp_info.components["c3"].includedirs = ["include"]
            """)
        c.save({"conanfile.py": dep})
        c.run("create .")
        c.run(f"install --requires=dep/0.1 -g CMakeDeps -c tools.cmake.cmakedeps:new={new_value}")
        cmake = c.load("dep-config.cmake")
        assert 'set(dep_PACKAGE_PROVIDED_COMPONENTS MyCompC1 MyC2 c3)' in cmake


class TestCppInfoChecks:
    def test_check_exe_libs(self):
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                name = "dep"
                version = "0.1"
                def package_info(self):
                    self.cpp_info.libs = ["mylib"]
                    self.cpp_info.exe = "myexe"
            """)
        c.save({"conanfile.py": dep})
        c.run("create .")
        args = f"-g CMakeDeps -c tools.cmake.cmakedeps:new={new_value}"
        c.run(f"install --requires=dep/0.1 {args}", assert_error=True)
        assert "Error in generator 'CMakeDeps': dep/0.1 " 'cpp_info has both .exe and .libs' in c.out

    def test_exe_no_location(self):
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                name = "dep"
                version = "0.1"
                def package_info(self):
                    self.cpp_info.exe = "myexe"
            """)
        c.save({"conanfile.py": dep})
        c.run("create .")
        args = f"-g CMakeDeps -c tools.cmake.cmakedeps:new={new_value}"
        c.run(f"install --requires=dep/0.1 {args}", assert_error=True)
        assert "Error in generator 'CMakeDeps': dep/0.1 cpp_info has .exe and no .location" in c.out

    def test_check_exe_wrong_type(self):
        c = TestClient()
        dep = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                name = "dep"
                version = "0.1"
                def package_info(self):
                    self.cpp_info.type = "shared-library"
                    self.cpp_info.exe = "myexe"
            """)
        c.save({"conanfile.py": dep})
        c.run("create .")
        args = f"-g CMakeDeps -c tools.cmake.cmakedeps:new={new_value}"
        c.run(f"install --requires=dep/0.1 {args}", assert_error=True)
        assert "dep/0.1 cpp_info incorrect .type shared-library for .exe myexe" in c.out



def test_multiple_find_package_subfolder():
    c = TestClient()
    conanfile = textwrap.dedent("""
    from conan import ConanFile
    class TestPackage(ConanFile):
        name = "matrix"
        version = "1.0"
        def package_info(self):
            self.cpp_info.system_libs = ["mysystemlib"]
        """)
    c.save({"conanfile.py": conanfile})
    c.run("create .")

    cmake = textwrap.dedent("""
        cmake_minimum_required(VERSION 3.15)
        project(app NONE)

        find_package(matrix CONFIG REQUIRED)
        add_subdirectory(subdir)
        """)
    subcmake = textwrap.dedent("""
        cmake_minimum_required(VERSION 3.15)
        project(subdir NONE)

        find_package(matrix CONFIG REQUIRED)
        """)
    conanfile = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.cmake import CMake
        class Pkg(ConanFile):
            requires = "matrix/1.0"
            generators = "CMakeToolchain", "CMakeDeps"
            settings = "os", "compiler", "build_type", "arch"
            def build(self):
                cmake = CMake(self)
                cmake.configure()
        """)
    c.save({"conanfile.py": conanfile,
            "CMakeLists.txt": cmake,
            "subdir/CMakeLists.txt": subcmake}, clean_first=True)

    c.run(f"build . -c tools.cmake.cmakedeps:new={new_value}")
    assert "find_package(matrix)" in c.out
    assert "target_link_libraries(... matrix::matrix)" in c.out
    assert "Conan: Target declared imported INTERFACE library 'matrix::matrix'" in c.out
