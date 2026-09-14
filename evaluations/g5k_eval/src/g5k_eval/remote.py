import concurrent.futures
import shlex

import enoslib as en
from fabric import Connection

# remote command helpers


def create_fabric_conn(host, user="root") -> Connection:
    host_addr = host.address if hasattr(host, "address") else host
    return Connection(host=host_addr, user=user)


def bg_inner_cmd(stdout, stderr, cmd):
    # Start cmd on each host with setsid so it survives SSH channel close
    return (
        f'mkdir -p "$(dirname {stdout})" "$(dirname {stderr})" && '
        f"setsid bash -c {shlex.quote(cmd)} > {stdout} 2> {stderr} < /dev/null &"
    )


def run_cmd_bg_enos(cmd, hosts, *, stdout, stderr, task_name="bg"):

    return en.run_command(
        bg_inner_cmd(stdout, stderr, cmd), roles=hosts, task_name=task_name
    )


def ssh_bg(cmd, host, *, stdout, stderr, user="root"):
    # Start command in the bg of the host via ssh
    conn = create_fabric_conn(host, user=user)
    conn.run(
        bg_inner_cmd(stdout, stderr, cmd), disown=True, hide=True, warn=True, pty=False
    )


# run a command synchronously no all given hosts in parallel
def run_cmd_ssh_parallel(cmd, hosts, *, check=True):
    def run_cmd_ssh_one_host(cmd, host, *, user="root", check=True):
        conn = create_fabric_conn(host, user=user)
        result = conn.run(cmd, hide=True, warn=not check, pty=False)

        if check and result.failed:
            raise RuntimeError(
                f"ssh to {conn.host} failed ({result.return_code}): {result.stderr.strip()}"
            )
        return result

    hosts = list(hosts)
    if not hosts:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as ex:
        return list(ex.map(lambda h: run_cmd_ssh_one_host(cmd, h, check=check), hosts))


# send a kill signal to the names of program on the given nodes
def send_pkill_hosts(hosts, names):
    joined = " ; ".join(f"pkill -9 {n} || true" for n in names)
    return run_cmd_ssh_parallel(joined, hosts, check=False)
