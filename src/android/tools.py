"""
Copyright (c) 2011 Michael Elsdoerfer <michael@elsdoerfer.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
import os
import subprocess


__all__ = ('ProgramFailedError', 'Aapt', 'Aidl', 'LlvmRs', 'ApkBuilder',
           'Dx', 'JarSigner', 'NdkBuild', 'NdkClean', 'JavaC', 'ZipAlign')


class ProgramFailedError(RuntimeError):
    """Holds information about the failure.
    """

    def __init__(self, cmdline, returncode, stdout=None, stderr=None):
        if isinstance(cmdline, (tuple, list)):
            cmdline = " ".join(cmdline)
        self.cmdline = cmdline
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    @property
    def message(self):
        return self.__str__()

    def __unicode__(self):
        return u'%s failed with code %s' % (
            self.cmdline, self.returncode)

    def __str__(self):
        return self.__unicode__().encode('ascii', '?')


class Program(object):

    def __init__(self, executable, framework=None):
        self.executable = executable
        # Some tools need to know the SDK environment they are running in
        self.framework = framework

    def extend_args(self, args, new, condition=True):
        """Helper which will extend the argument list ``args``
        with the list ``new``, but only if ``new`` contains
        no ``None`` items, and only if a specified ``condition``
        is ``True``.
        """
        if not None in new and condition:
            args.extend(new)

    def __repr__(self):
        return '%s <%s>' % (
            self.__class__.__name__, repr(self.executable))

    def __call__(self, arguments, env=None, shell=False):
        """Note that this returns the command line that was executed,
        so it can be logged.

        Child implementations must not forget to pass this return value
        along to their caller.
        """
        cmdline = [self.executable] + arguments
        if shell and not sys.platform=="win32":
            # This is required for scripts that lack the +x flag
            cmdline.insert(0, '/bin/sh')
        cmdline_str = " ".join(cmdline)

        custom_env = os.environ.copy()
        custom_env.update(env or {})

        process = subprocess.Popen(
            cmdline,
            shell=True if sys.platform=="win32" else False,
            env=custom_env,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)
        process.wait()
        if process.returncode != 0:
            raise ProgramFailedError(
                cmdline_str,
                process.returncode, process.stderr.read(),
                process.stdout.read())

        return cmdline_str


class Aapt(Program):
    """Interface to the ``aapt`` tool used to package resources.
    """

    def __call__(self, command, manifest=None, resource_dir=None,
                 asset_dir=None, include=[], apk_output=None,
                 r_output=None, configurations=None,
                 rename_manifest_package=None, overwrite_version_code=None,
                 overwrite_version_name=None,
                 make_dirs=None, overwrite=None,
                 extra_args = []):
        """
        command
            The APPT command to execute.

        manifest
            AndroidManifest.xml to include in zip (-M).

        resource_dir
            Directory in which to find resources (-S).

        asset_dir
            Additional directory in which to find raw asset files (-A).

        include
            List of packages to include in the base set (-I).

        apk_output
            The apk file to output (-F).

        r_output
            Where to output R.java resource constant definitions (-J).

        make_dirs
            Make package directories for ``r_output`` option (-m).

        extra_args
            List of extra arguments.
        """

        args = [command]
        self.extend_args(args, ['-m'], make_dirs)
        self.extend_args(args, ['-M', manifest])
        self.extend_args(args, ['-S', resource_dir])
        self.extend_args(args, ['-A', asset_dir])
        self.extend_args(args, ['-c', configurations])
        if overwrite_version_code:
            self.extend_args(
                args, ['--version-code', "%s" % overwrite_version_code])
        self.extend_args(args, ['--version-code', overwrite_version_name])
        self.extend_args(
            args, ['--rename-manifest-package', rename_manifest_package])
        for item in include:
            self.extend_args(args, ['-I', item])
        self.extend_args(args, ['-F', apk_output])
        self.extend_args(args, ['-J', r_output])
        self.extend_args(args, ['-f'], overwrite)
        self.extend_args(args, extra_args )
        return Program.__call__(self, args)


class Aidl(Program):
    """Interface to the ``aidl`` tool used to compile .aidl files.
    """

    def __call__(self, aidl_file, preprocessed=None, search_path=None,
                 output_folder=None):
        """
        aidl_file
            An aidl interface file (INPUT).

        preprocessed
            File created by --preprocess to import (-p).

        search_path
            Search path for import statements (-I).

        output_folder
            Base output folder for generated files (-o).
        """
        args = []
        self.extend_args(args, ['-p%s' % preprocessed], preprocessed)
        self.extend_args(args, ['-I%s' % search_path], search_path)
        self.extend_args(args, ['-o%s' % output_folder], output_folder)
        self.extend_args(args, [aidl_file])
        return Program.__call__(self, args)


class LlvmRs(Program):
    """Interface to the command line llvm renderscript compiler, ``llvm-rs-cc``
    """

    def __call__(self, resource_dir, resource_gen_dir, source_files, include_dirs):
        args = []
        for include in include_dirs:
            self.extend_args(args, ['-I', include])
        self.extend_args(args, ['-o', resource_dir])
        self.extend_args(args, ['-java-reflection-path-base', resource_gen_dir])
        for filename in source_files:
            self.extend_args(args, [filename])
        return Program.__call__(self, args)


class NdkBuild(Program):
    """Interface to the command line c/c++ compiler, ``ndk-build``
    """

    def __call__(self, project_path):
        """
        project_path
            Location of the project
        """
        args = []
        self.extend_args(args, ["-C", project_path])
        return Program.__call__(self, args)

class NdkClean(Program):
    """Interface to the command linec/c++ cleaner, ``ndk-build clean``
    """

    def __call__(self, project_path):
        args = []
        self.extend_args(args, ["clean"])
        self.extend_args(args, ["-C", project_path])
        return Program.__call__(self, args)


class JavaC(Program):
    """Interface to the Java command line compiler, ``javac``.
    """

    def __call__(self, files, destdir=None, encoding=None,
                 target=None, classpath=[], bootclasspath=None,
                 debug=None):
        """
        files
            Files to be compiled (<source files>).

        destdir
            Where to place generated class files (-d).

        classpath
            Where to find user class files and annotation
            processors (-classpath). Expected to be a list.

        bootclasspath
            Location of bootstrap class files (-bootclasspath).

        encoding
            Character encoding used by source files (-encoding).

        target
            Generate class files for specific VM version (-target).
        """
        args = []
        self.extend_args(args, ['-encoding', encoding])
        self.extend_args(args, ['-target', target])
        self.extend_args(args, ['-source', target])
        self.extend_args(args, ['-d', destdir])
        self.extend_args(
            args, ['-classpath', ":".join(classpath)], classpath)
        self.extend_args(args, ['-bootclasspath', bootclasspath])
        args.extend(['-g' if debug else '-g:none'])
        args.extend(files)
        return Program.__call__(self, args)


class Dx(Program):
    """Interface to the ``dx`` command line tool which converts Java
    bytecode to Android's Dalvik bytecode.
    """

    def __call__(self, files, output=None):
        """
        files
            A set of class files, .zip/.jar/.apk archives or
            directories.

        output
            Target output file (--output).
        """
        args = ['--dex']
        self.extend_args(args, ["--output=%s" % output])
        args.extend(files)
        return Program.__call__(self, args)


class ApkBuilder(Program):
    """Interface to the ``apkbuilder`` command line tool.

    The version of ``apkbuilder`` included with the Android SDK is
    currently deprecated, consult the README for information on where
    to find a version better suited to be used.
    """

    def __call__(self, outputfile, dex=None, zips=[], source_dirs=[],
                 jar_paths=[], native_dirs=[]):
        """
        outputfile
            The APK file to create (<out archive>).

        dex
            The code of the app (optional if no code) (-f).

        zips
            List of zip archives to add (-z).

        source_dirs
            Adds the java resources found in that folder (-rf).

        jar_paths
            List of jar files or folders containing jar files to add (-rj).

        native_dirs
            List of folders containing native libraries to add (-nf).
        """
        args = [outputfile]
        args.extend(['-u'])  # unsigned
        self.extend_args(args, ['-f', dex])
        for zip in zips:
            args.extend(['-z', zip])
        for source_dir in source_dirs:
            args.extend(['-rf', source_dir])
        for item in jar_paths:
            args.extend(['-rj', item])
        for item in native_dirs:
            args.extend(['-nf', item])
        return Program.__call__(
            self, args,
            {'ANDROID_SDK_DIR': self.framework.sdk_dir}, shell=True)


class JarSigner(Program):
    """Interface to the ``jarsigner`` command line tool.
    """

    def __call__(self, jarfile, keystore, alias, password):
        args = []
        args.extend(['-keystore', keystore])
        args.extend(['-storepass', password])
        args.extend(['-digestalg', 'SHA1'])
        args.extend(['-sigalg', 'MD5withRSA'])
        args.extend([jarfile])
        args.extend([alias])
        return Program.__call__(self, args)


class ZipAlign(Program):
    """Interface to the ``zipalign`` command line tool.
    """

    def __call__(self, infile, outfile, align, force=None):
        args = []
        self.extend_args(args, ['-f'], force)
        args.extend(["%s" % align])
        args.extend([infile])
        args.extend([outfile])
        return Program.__call__(self, args)
