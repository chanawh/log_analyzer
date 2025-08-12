import logging
import os
import stat
import posixpath
import paramiko


class SSHBrowser:
    def __init__(self):
        self.ssh = None
        self.sftp = None
        self.current_path = "/"

    def connect(self, host, username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=username, password=password)
        self.sftp = self.ssh.open_sftp()
        self.current_path = self.sftp.normalize(".")

    def list_dir(self, path):
        try:
            items = self.sftp.listdir_attr(path)
            return [(item.filename, stat.S_ISDIR(item.st_mode)) for item in items]
        except Exception as e:
            logging.error(f"Failed to list directory: {e}")
            return []

    def change_dir(self, subdir):
        if subdir == "..":
            self.current_path = os.path.dirname(self.current_path.rstrip("/"))
        else:
            self.current_path = os.path.join(self.current_path, subdir)
        return self.list_dir(self.current_path)

    def download_file(self, filename):
        remote_path = posixpath.join(self.current_path, filename)
        local_path = os.path.join(os.getcwd(), filename)
        try:
            remote_files = self.sftp.listdir(self.current_path)
            if filename not in remote_files:
                logging.error(
                    f"File '{filename}' not found in remote directory '{self.current_path}'"
                )
                return ""
            self.sftp.get(remote_path, local_path)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                logging.info(
                    f"Downloaded file to {local_path} ({os.path.getsize(local_path)} bytes)"
                )
            else:
                logging.warning(f"Downloaded file is empty or missing: {local_path}")
            return local_path
        except FileNotFoundError:
            logging.error(f"Remote file not found: {remote_path}")
            return ""
        except Exception as e:
            logging.error(f"Failed to download file: {e}")
            return ""

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
