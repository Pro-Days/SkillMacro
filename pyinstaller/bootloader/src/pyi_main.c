/*
 * ****************************************************************************
 * Copyright (c) 2013-2023, PyInstaller Development Team.
 *
 * Distributed under the terms of the GNU General Public License (version 2
 * or later) with exception for distributing the bootloader.
 *
 * The full license is in the file COPYING.txt, distributed with this software.
 *
 * SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
 * ****************************************************************************
 */

/*
 * Bootloader for a packed executable.
 */

#ifdef _WIN32
    #include <windows.h>
    #include <wchar.h>
#endif
#ifdef __CYGWIN__
    #include <sys/cygwin.h>  /* cygwin_conv_path */
    #include <windows.h>  /* SetDllDirectoryW */
    /* NOTE: SetDllDirectoryW is part of KERNEL32, which is automatically
     * linked by Cygwin, so we do not need to explicitly link any
     * win32 libraries. */
#endif
#include <stdio.h>  /* FILE */
#include <stdlib.h> /* calloc */
#include <string.h> /* memset */

#if defined(__linux__)
    #include <sys/prctl.h> /* prctl() */
#endif

/* PyInstaller headers. */
#include "pyi_main.h"
#include "pyi_global.h"  /* PATH_MAX */
#include "pyi_path.h"
#include "pyi_archive.h"
#include "pyi_utils.h"
#include "pyi_pythonlib.h"
#include "pyi_launch.h"
#include "pyi_win32_utils.h"
#include "pyi_splash.h"
#include "pyi_apple_events.h"


/* Console hiding/minimization options. Windows only. */
#if defined(_WIN32) && !defined(WINDOWED)

#define HIDE_CONSOLE_OPTION_HIDE_EARLY "hide-early"
#define HIDE_CONSOLE_OPTION_HIDE_LATE "hide-late"
#define HIDE_CONSOLE_OPTION_MINIMIZE_EARLY "minimize-early"
#define HIDE_CONSOLE_OPTION_MINIMIZE_LATE "minimize-late"

#endif


static int
_pyi_allow_pkg_sideload(const char *executable)
{
    FILE *file = NULL;
    uint64_t magic_offset;
    unsigned char magic[8];

    /* First, find the PKG sideload signature in the executable */
    file = pyi_path_fopen(executable, "rb");
    if (!file) {
        return -1;
    }

    /* Prepare magic pattern */
    memcpy(magic, MAGIC_BASE, sizeof(magic));
    magic[3] += 0x0D;  /* 0x00 -> 0x0D */

    /* Find magic pattern in the executable */
    magic_offset = pyi_utils_find_magic_pattern(file, magic, sizeof(magic));
    if (magic_offset == 0) {
        fclose(file);
        return 1; /* Error code 1: no embedded PKG sideload signature */
    }

    /* TODO: expand the verification by embedding hash of the PKG file */

    /* Allow PKG to be sideloaded */
    return 0;
}

int
pyi_main(int argc, char * argv[])
{
    /*  archive_status contain status information of the main process. */
    ARCHIVE_STATUS *archive_status = NULL;
    SPLASH_STATUS *splash_status = NULL;
    char executable[PATH_MAX];
    char archivefile[PATH_MAX];
    int rc = 0;
    int in_child = 0;
    char *extractionpath = NULL;

#ifdef _MSC_VER
    /* Visual C runtime incorrectly buffers stderr */
    setbuf(stderr, (char *)NULL);
#endif  /* _MSC_VER */

    VS("PyInstaller Bootloader 6.x\n");

    archive_status = pyi_arch_status_new();
    if (archive_status == NULL) {
        return -1;
    }
    if ((! pyi_path_executable(executable, argv[0])) ||
        (! pyi_path_archivefile(archivefile, executable))) {
        return -1;
    }

    /* For the curious:
     * On Windows, the UTF-8 form of MEIPASS2 is passed to pyi_setenv, which
     * decodes to UTF-16 before passing it to the Windows API. So the var's value
     * is full unicode.
     *
     * On OS X/Linux, the MEIPASS2 value is passed as the bytes received from the OS.
     * Only Python will care about its encoding, and it is passed to Python using
     * PyUnicode_DecodeFSDefault.
     */

    extractionpath = pyi_getenv("_MEIPASS2");

    /* NOTE: record the in-child status here, because extractionpath
     * might get overwritten later on (on Windows and macOS, single
     * process is used for --onedir mode). */
    in_child = (extractionpath != NULL);
    if (in_child) {
        /* Check if _PYI_ONEDIR_MODE is set to 1; this is set by linux/unix
         * bootloaders when they restart themselves within the same process
         * to achieve single-process onedir execution mode. This case should
         * be treated as if extractionpath was not set at this point yet,
         * i.e., in_child needs to be reset to 0. */
        char *pyi_onedir_mode = pyi_getenv("_PYI_ONEDIR_MODE");
        if (pyi_onedir_mode) {
            if (strcmp(pyi_onedir_mode, "1") == 0) {
                in_child = 0;
            }
            free(pyi_onedir_mode);
            pyi_unsetenv("_PYI_ONEDIR_MODE");
        }
    }

    /* If the Python program we are about to run invokes another PyInstaller
     * one-file program as subprocess, this subprocess must not be fooled into
     * thinking that it is already unpacked. Therefore, PyInstaller deletes
     * the _MEIPASS2 variable from the environment.
     */

    pyi_unsetenv("_MEIPASS2");

    VS("LOADER: _MEIPASS2 is %s\n", (extractionpath ? extractionpath : "not set"));

    /* Try opening the archive; first attempt to read it from executable
     * itself (embedded mode), then from a stand-alone pkg file (sideload mode)
     */
    if (!pyi_arch_setup(archive_status, executable, executable)) {
        if (!pyi_arch_setup(archive_status, archivefile, executable)) {
            FATALERROR("Cannot open PyInstaller archive from executable (%s) or external archive (%s)\n",
                       executable, archivefile);
            return -1;
        } else if (extractionpath == NULL) {
            /* Check if package side-load is allowed. But only on the first
             * run, in the parent process (i.e., when extractionpath is not
             * yet set). */
            rc = _pyi_allow_pkg_sideload(executable);
            if (rc != 0) {
                FATALERROR("Cannot side-load external archive %s (code %d)!\n", archivefile, rc);
                return -1;
            }
        }
    }

#if defined(_WIN32) && !defined(WINDOWED)
    /* Early console hiding/minimization */
    const char *hide_console_option = pyi_arch_get_option(archive_status, "pyi-hide-console");
    if (hide_console_option != NULL) {
        if (strcmp(hide_console_option, HIDE_CONSOLE_OPTION_HIDE_EARLY) == 0) {
            pyi_win32_hide_console();
        } else if (strcmp(hide_console_option, HIDE_CONSOLE_OPTION_MINIMIZE_EARLY) == 0) {
            pyi_win32_minimize_console();
        }
    }
#endif

#if defined(__linux__)
    char *processname = NULL;

    /* Set process name on linux. The environment variable is set by
       parent launcher process. */
    processname = pyi_getenv("_PYI_PROCNAME");
    if (processname) {
        VS("LOADER: restoring linux process name from _PYI_PROCNAME: %s\n", processname);
        if (prctl(PR_SET_NAME, processname, 0, 0)) {
            FATALERROR("LOADER: failed to set linux process name!\n");
            return -1;
        }
        free(processname);
    }
    pyi_unsetenv("_PYI_PROCNAME");

#endif  /* defined(__linux__) */

    /* These are passed on to python interpreter, so they show up in sys.argv */
    archive_status->argc = argc;
    archive_status->argv = argv;

    /* Check if we need to unpack the embedded archive (onefile build, or onedir
     * build in MERGE mode). If we do, create the temporary directory. */
    if (!in_child && archive_status->needs_to_extract) {
        /* On Windows, initialize security descriptor for temporary directory.
         * This is required by `pyi_win32_mkdir()` calls made when creating application's
         * temporary directory and its sub-directories during file extration. */
#if defined(_WIN32)
        VS("LOADER: initializing security descriptor for temporary directory...\n");
        if (pyi_win32_initialize_security_descriptor() == -1) {
            FATALERROR("Failed to initialize security descriptor for temporary directory!\n");
            return -1;
        }
#endif

        VS("LOADER: creating temporary directory...\n");
        if (pyi_arch_create_tempdir(archive_status) == -1) {
            return -1;
        }
        VS("LOADER: created temporary directory: %s\n", archive_status->temppath);
    }

#if defined(_WIN32) || defined(__APPLE__)

    /* On Windows and Mac use single-process for --onedir mode. */
    if (!extractionpath && !archive_status->needs_to_extract) {
        VS("LOADER: No need to extract files to run; setting extractionpath to homepath\n");
        extractionpath = archive_status->homepath;
    }

#else

    /* On other OSes (linux and unix-like), we also use single-process for
     * --onedir mode. However, in contrast to Windows and macOS, we need to
     * set environment (i.e., LD_LIBRARY_PATH) and then restart/replace the
     * process via exec() without fork() for the environment changes (library
     * search path) to take effect. */
     if (!extractionpath && !archive_status->needs_to_extract) {
        VS("LOADER: No need to extract files to run; setting up environment and restarting bootloader...\n");

        /* Set _MEIPASS2, so that the restarted bootloader process will enter
         * the codepath that corresponds to child process. */
        pyi_setenv("_MEIPASS2", archive_status->homepath);

        /* Set _PYI_ONEDIR_MODE to signal to restarted bootloader that it
         * should reset in_child variable even though it is operating in
         * child-process mode. This is necessary for splash screen to
         * be shown. */
        pyi_setenv("_PYI_ONEDIR_MODE", "1");

        /* Set up the library search path (by modifying LD_LIBRARY_PATH or
         * equivalent), so that the restarted process will be able to find
         * the collected libraries in the top-level application directory
         * (i.e., archive_status->homepath).
         */
        if (pyi_utils_set_library_search_path(archive_status->homepath) == -1) {
            return -1;
        }

        /* Restart the process. The helper function performs exec() without
         * fork(), so we never return from the call. */
        if (pyi_utils_replace_process(executable, argc, argv) == -1) {
            return -1;
        }
    }

#endif


#if defined(_WIN32) || defined(__CYGWIN__)
    if (extractionpath) {
        /* Add extraction folder to DLL search path */
        wchar_t dllpath_w[PATH_MAX];
#if defined(__CYGWIN__)
        /* Cygwin */
        if (cygwin_conv_path(CCP_POSIX_TO_WIN_W | CCP_RELATIVE, extractionpath, dllpath_w, PATH_MAX) != 0) {
            FATAL_PERROR("cygwin_conv_path", "Failed to convert DLL search path!\n");
            return -1;
        }
#else
        /* Windows */
        if (pyi_win32_utils_from_utf8(dllpath_w, extractionpath, PATH_MAX) == NULL) {
            FATALERROR("Failed to convert DLL search path!\n");
            return -1;
        }
#endif  /* defined(__CYGWIN__) */
        VS("LOADER: SetDllDirectory(%S)\n", dllpath_w);
        SetDllDirectoryW(dllpath_w);
    }
#endif  /* defined(_WIN32) || defined(__CYGWIN__) */

    /*
     * Check for splash screen resources.
     * For the splash screen function to work PyInstaller
     * needs to bundle tcl/tk with the application. This library
     * is the same as tkinter uses.
     */
    splash_status = pyi_splash_status_new();

    if (!in_child && pyi_splash_setup(splash_status, archive_status) == 0) {
        /*
         * Splash resources found, start splash screen
         * If in onefile mode extract the required binaries
         */
        if ((!pyi_splash_extract(archive_status, splash_status)) &&
            (!pyi_splash_attach(splash_status))) {
            /* Everything was initialized, so it is safe to start
             * the splash screen */
            pyi_splash_start(splash_status, executable);
        }
        else {
            /* Error attaching tcl/tk libraries.
             * It may have happened that the libraries got (partly)
             * loaded, so close them by finalizing the splash status */
            pyi_splash_finalize(splash_status);
            pyi_splash_status_free(&splash_status);
        }
    }
    else {
        /* No splash screen resources found */
        pyi_splash_status_free(&splash_status);
    }

    if (extractionpath) {
        VS("LOADER: Already in the child - running user's code.\n");

        /*  If binaries were extracted to temppath,
         *  we pass it through status variable
         */
        if (strcmp(archive_status->homepath, extractionpath) != 0) {
            if (snprintf(archive_status->temppath, PATH_MAX,
                         "%s", extractionpath) >= PATH_MAX) {
                VS("LOADER: temppath exceeds PATH_MAX\n");
                return -1;
            }
            /*
             * Temp path exits - set appropriate flag and change
             * status->mainpath to point to temppath.
             */
            archive_status->has_temp_directory = true;
            strcpy(archive_status->mainpath, archive_status->temppath);
        }

#if defined(__APPLE__) && defined(WINDOWED)
        if (!in_child) {
            /* Initialize argc_pyi and argv_pyi with argc and argv */
            if (pyi_utils_initialize_args(archive_status->argc, archive_status->argv) < 0) {
                return -1;
            }
            /* Optional argv emulation for onedir .app bundles */
            if (pyi_arch_get_option(archive_status, "pyi-macos-argv-emulation") != NULL) {
                /* Install event handlers */
                pyi_apple_install_event_handlers();
                /* Process Apple events; this updates argc_pyi/argv_pyi
                 * accordingly */
                pyi_apple_process_events(0.25);  /* short_timeout (250 ms) */
                /* Uninstall event handlers */
                pyi_apple_uninstall_event_handlers();
                /* The processing of Apple events swallows up the initial
                 * activation event, whatever it might have been (typically
                 * oapp, but could also be odoc or GURL if application is
                 * launched in response to request to open file/URL).
                 * This seems to cause issues with some UI frameworks
                 * (Tcl/Tk, in particular); so we submit a new oapp event
                 * to ourselves...
                 */
                 pyi_apple_submit_oapp_event();
            }
            /* Update pointer to arguments; regardless of argv-emulation,
             * because pyi_utils_initialize_args() also filters out
             * -psn_xxx argument.
             */
            pyi_utils_get_args(&archive_status->argc, &archive_status->argv);
        }
#endif

#if defined(_WIN32) && !defined(WINDOWED)
        /* Late console hiding/minimization; this should turn out to be a
         * no-op in child processes of onefile programs or in spawned
         * additional subprocesses using the executable, because the
         * process does not own the console.
         */
        if (hide_console_option != NULL) {
            if (strcmp(hide_console_option, HIDE_CONSOLE_OPTION_HIDE_LATE) == 0) {
                pyi_win32_hide_console();
            } else if (strcmp(hide_console_option, HIDE_CONSOLE_OPTION_MINIMIZE_LATE) == 0) {
                pyi_win32_minimize_console();
            }
        }
#endif

        /* Use message queue to have Windows stop showing spinning-wheel
         * cursor indicating that the program is starting. For details,
         * see the corresponding comment in the onefile code-path.
         *
         * In onedir mode, this aims to make noconsole programs that do
         * not display any UI appear to start faster.
         */
#if defined(_WIN32) && defined(WINDOWED)
        if (!splash_status) {
            MSG msg;
            PostMessageW(NULL, 0, 0, 0);
            GetMessageW(&msg, NULL, 0, 0);
        }
#endif

        /* Main code to initialize Python and run user's code. */
        pyi_launch_initialize(archive_status);
        rc = pyi_launch_execute(archive_status);
        pyi_launch_finalize(archive_status);

        /* Clean up splash screen resources; required when in single-process
         * execution mode, i.e. when using --onedir on Windows or macOS. */
        pyi_splash_finalize(splash_status);
        pyi_splash_status_free(&splash_status);

#if defined(__APPLE__) && defined(WINDOWED)
        /* Clean up arguments that were used with Apple event processing .*/
        pyi_utils_free_args();
#endif
    }
    else {

        /* status->temppath is created if necessary. */
        if (pyi_launch_extract_binaries(archive_status, splash_status)) {
            VS("LOADER: temppath is %s\n", archive_status->temppath);
            VS("LOADER: Error extracting binaries\n");
            return -1;
        }

        /* At this point, extraction to temporary directory is complete,
         * and we can free the Windows security descriptor that was used
         * during creation of temporary directory and its sub-directories. */
#if defined(_WIN32)
        pyi_win32_free_security_descriptor();
#endif

        /* Run the 'child' process, then clean up. */

        VS("LOADER: Executing self as child\n");
        pyi_setenv("_MEIPASS2", archive_status->temppath);

        VS("LOADER: set _MEIPASS2 to %s\n", pyi_getenv("_MEIPASS2"));

#if defined(__linux__)
        char tmp_processname[16]; /* 16 bytes as per prctl() man page */

        /* Pass the process name to child via environment variable. */
        if (!prctl(PR_GET_NAME, tmp_processname, 0, 0)) {
            VS("LOADER: linux: storing process name into _PYI_PROCNAME: %s\n", tmp_processname);
            pyi_setenv("_PYI_PROCNAME", tmp_processname);
        }

#endif  /* defined(__linux__) */

        /* On OSes other than Windows and macOS, we need to set library
         * search path (via LD_LIBRARY_PATH or equivalent). */
#if !defined(_WIN32) && !defined(__APPLE__)
        if (pyi_utils_set_library_search_path(archive_status->temppath) == -1) {
            return -1;
        }
#endif /* !defined(_WIN32) && !defined(__APPLE__) */

        /* Transform parent to background process on OSX only. */
        pyi_parent_to_background();

#if defined(_WIN32) && !defined(WINDOWED)
        /* Late console hiding/minimization */
        if (hide_console_option != NULL) {
            if (strcmp(hide_console_option, HIDE_CONSOLE_OPTION_HIDE_LATE) == 0) {
                pyi_win32_hide_console();
            } else if (strcmp(hide_console_option, HIDE_CONSOLE_OPTION_MINIMIZE_LATE) == 0) {
                pyi_win32_minimize_console();
            }
        }
#endif

        /* When a windowed/noconsole process is launched on Windows, the
         * OS displays a spinning-wheel cursor to indicate that the program
         * is starting. This goes on for a fixed amount of time or until
         * the process uses some UI functionality (creates a window, uses
         * message queue). In a PyInstaller onefile application, the parent
         * process displays a window only if splash screen is used; the UI
         * is created and shown by the child process. To prevent the
         * "program is starting" cursor being shown for the full duration
         * (i.e., after the child process shows its UI), make use of
         * message queue to signal the OS that the process is alive.
         *
         * For onefile, we do this just before we spawn the child process,
         * so that the "program is starting" cursor is shown while the
         * parent process unpacks the application.
         *
         * See: https://github.com/python/cpython/blob/v3.12.2/PC/launcher.c#L765-L779
         */
#if defined(_WIN32) && defined(WINDOWED)
        if (!splash_status) {
            MSG msg;
            PostMessageW(NULL, 0, 0, 0);
            GetMessageW(&msg, NULL, 0, 0);
        }
#endif

        /* Run user's code in a subprocess and pass command line arguments to it. */
        rc = pyi_utils_create_child(executable, archive_status, argc, argv);

        VS("LOADER: Back to parent (RC: %d)\n", rc);

        VS("LOADER: Doing cleanup\n");

        /* Finalize splash screen before temp directory gets wiped, since the splash
         * screen might hold handles to shared libraries inside the temp dir. Those
         * wouldn't be removed, leaving the temp folder behind. */
        pyi_splash_finalize(splash_status);
        pyi_splash_status_free(&splash_status);

        if (archive_status->has_temp_directory == true) {
            pyi_recursive_rmdir(archive_status->temppath);
        }
        pyi_arch_status_free(archive_status);

        /* Re-raise child's signal, if necessary (non-Windows only) */
#ifndef _WIN32
        pyi_utils_reraise_child_signal();
#endif
    }
    return rc;
}
