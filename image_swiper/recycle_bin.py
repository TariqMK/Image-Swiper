"""Windows Recycle Bin operations."""
import winshell


def delete_file(path):
    winshell.delete_file(str(path), no_confirm=True, allow_undo=True)


def restore_file(path):
    winshell.undelete(str(path))
