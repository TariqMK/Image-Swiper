"""Native trash operations; programmatic restore is Windows-only."""
import sys

CAN_RESTORE = sys.platform == 'win32'

if CAN_RESTORE:
    import winshell
else:
    from send2trash import send2trash


def delete_file(path):
    if CAN_RESTORE:
        winshell.delete_file(str(path), no_confirm=True, allow_undo=True)
    else:
        send2trash(str(path))


def restore_file(path):
    if not CAN_RESTORE:
        raise NotImplementedError('Restore this file manually from your system Trash.')
    winshell.undelete(str(path))
