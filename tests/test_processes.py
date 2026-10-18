"""Background tools must never create a Windows console while scanning."""
import subprocess
import unittest
from unittest.mock import Mock, patch

from image_swiper.processes import run_background, stop_background_tools


class BackgroundProcessTests(unittest.TestCase):
    def test_windows_hides_console_and_disconnects_standard_streams(self):
        with patch('image_swiper.processes.sys.platform', 'win32'), patch.object(
            subprocess, 'CREATE_NO_WINDOW', 0x08000000, create=True
        ), patch('image_swiper.processes.subprocess.Popen') as run:
            run.return_value.communicate.return_value = ('metadata', '')
            run.return_value.returncode = 0
            run_background(['ffmpeg', '-version'], timeout=10, check=True)
        options = run.call_args.kwargs
        self.assertEqual(options['creationflags'], 0x08000000)
        self.assertEqual(options['stdin'], subprocess.DEVNULL)
        self.assertEqual(options['stdout'], subprocess.DEVNULL)
        self.assertEqual(options['stderr'], subprocess.DEVNULL)
        run.return_value.communicate.assert_called_once_with(timeout=10)

    def test_capture_output_preserves_metadata_on_all_platforms(self):
        for platform in ('win32', 'darwin', 'linux'):
            with self.subTest(platform=platform), patch('image_swiper.processes.sys.platform', platform), patch.object(
                subprocess, 'CREATE_NO_WINDOW', 0x08000000, create=True
            ), patch('image_swiper.processes.subprocess.Popen') as run:
                run.return_value.communicate.return_value = ('metadata', '')
                run.return_value.returncode = 0
                result = run_background(['ffprobe', 'synthetic.mp4'], capture_output=True, text=True, timeout=5)
                self.assertEqual(result.stdout, 'metadata')
                options = run.call_args.kwargs
                self.assertEqual(options['stdout'], subprocess.PIPE)
                self.assertEqual(options['stderr'], subprocess.PIPE)
                self.assertEqual('creationflags' in options, platform == 'win32')

    def test_shutdown_kills_running_tools_and_rejects_new_work(self):
        process = Mock()
        with patch('image_swiper.processes._processes', {process}), patch('image_swiper.processes._stopping', False):
            stop_background_tools()
            process.kill.assert_called_once()
            with patch('image_swiper.processes.subprocess.Popen') as start:
                with self.assertRaises(RuntimeError):
                    run_background(['ffmpeg', '-version'])
                start.assert_not_called()

    def test_timeout_kills_and_reaps_process(self):
        process = Mock(returncode=0)
        process.communicate.side_effect = [subprocess.TimeoutExpired('ffprobe', 5), ('', '')]
        with patch('image_swiper.processes.subprocess.Popen', return_value=process):
            with self.assertRaises(subprocess.TimeoutExpired):
                run_background(['ffprobe'], timeout=5)
        process.kill.assert_called_once()
        self.assertEqual(process.communicate.call_count, 2)
