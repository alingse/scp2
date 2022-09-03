import base64
import io
import logging
import uuid
import time

import click
import more_itertools
import paramiko


def new_ssh_chan(host, port, user):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, user)
    chan = ssh.invoke_shell()
    return chan


def file_to_64(file):
    with io.open(file, 'rb') as f:
        raw_content = f.read()
    base64_content = base64.b64encode(raw_content)
    content = base64_content.decode('utf8')
    return content


def chunk_upload_tmp(chan, tmpfile, content, chunksize=1024):
    chunked = more_itertools.ichunked(content, chunksize)
    for c in chunked:
        chunk = ''.join(c)
        cmd = f'echo "{chunk}" >> {tmpfile}\n'
        logging.info(cmd)
        chan.send(cmd)


def rebuild_from_tmp(chan, tmpfile, tofile):
    cmd = f"cat {tmpfile}|tr -d '\n'|base64 -d > {tofile}\n"
    logging.info(cmd)
    chan.send(cmd)

    cmd = f"rm {tmpfile}\n"
    logging.info(cmd)
    chan.send(cmd)


def log_chan_out(chan):
    log = b''
    while chan.recv_ready():
        log += chan.recv(1)
    print(log.decode())

    log = b''
    while chan.recv_stderr_ready():
        log += chan.recv_stderr(1)
    print(log.decode())


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
    chan = new_ssh_chan(host=host, port=port, user=user)
    time.sleep(1)

    logging.info(f'hello')
    chan.send('\n\n\n\nls\n')
    log_chan_out(chan)
    chan.send('\n\n')
    logging.info(f'world')
    time.sleep(1)

    tmpfile = tofile + '.tmp'
    logging.info(f'will temp write to {tmpfile}')

    log_chan_out(chan)
    chunk_upload_tmp(chan, tmpfile, content)
    chan.send('\n\n')
    time.sleep(1)
    log_chan_out(chan)
    rebuild_from_tmp(chan, tmpfile, tofile)
    chan.send('\n\n')
    time.sleep(1)
    log_chan_out(chan)

    logging.info('upload success')


if __name__ == '__main__':
    scp2()
