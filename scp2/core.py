import base64
import io
import logging
import uuid

import click
import more_itertools
import paramiko


def new_ssh_conn(host, port, user):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, user)
    return ssh


def file_to_64(file):
    with io.open(file, 'rb') as f:
        raw_content = f.read()
    base64_content = base64.b64encode(raw_content)
    content = base64_content.decode('utf8')
    return content


def chunk_upload_tmp(ssh_conn, tmpfile, content, chunksize=1024):
    chunked = more_itertools.ichunked(content, chunksize)
    for c in chunked:
        chunk = ''.join(c)
        cmd = f'echo "{chunk}" >> {tmpfile}'
        logging.info(cmd)

        ssh_conn.exec_command(cmd)


def rebuild_from_tmp(ssh_conn, tmpfile, tofile):
    cmd = f"cat {tmpfile}|tr -d '\n'|base64 -d > {tofile}"
    logging.info(cmd)
    ssh_conn.exec_command(cmd)

    cmd = f"rm {tmpfile}"
    logging.info(cmd)
    ssh_conn.exec_command(cmd)


# TODO: 兼容 scp 命令解析
# (也可以将来考虑有一套 python 解析所有 linux cmd 的 common click.header )
@click.command()
@click.option('-f', '--file', 'file', required=True, help='send file src')
@click.option('-u', '--uri', 'uri', required=True, help='the target dest')
@click.option('-p', '--port', 'port', default=22, help='host port')
def scp2(file, uri, port):
    head, tofile = uri.split(':')
    user, host = head.split('@')

    content = file_to_64(file)

    logging.basicConfig(level=logging.INFO)

    ssh_conn = new_ssh_conn(host=host, port=port, user=user)

    tmpfile = f'/tmp/{uuid.uuid4()}'
    logging.info(f'will temp write to {tmpfile}')

    chunk_upload_tmp(ssh_conn, tmpfile, content)
    rebuild_from_tmp(ssh_conn, tmpfile, tofile)

    logging.info('upload success')


if __name__ == '__main__':
    scp2()
